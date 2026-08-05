"""
HTTP API for the AI Agent Analytics Assistant.

Run:
  uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

import auth
from setup_database import DB_PATH, build_database, provision_customer
from sql_agent import SQLAgent
from vector_store import build_vector_store


# Example prompts shown in the UI — mix of personal and store-wide questions
EXAMPLE_QUESTIONS = [
    "How much have I spent in total?",
    "What have I ordered so far?",
    "Which products did I rate the highest?",
    "What are the top 5 products by total revenue?",
    "How many orders were placed in each city?",
    "What is the average product rating by category?",
]


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    error: str | None = None
    blocked: bool = False


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=8, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=200)
    password: str = Field(..., max_length=200)


class UserOut(BaseModel):
    id: int
    name: str
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class HistoryItem(BaseModel):
    id: int
    question: str
    row_count: int
    succeeded: bool
    created_at: str


# Singleton agent — heavy to initialise (embeddings + Chroma)
_agent: SQLAgent | None = None


def get_agent() -> SQLAgent:
    global _agent
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent is still starting up")
    return _agent


def ensure_ready() -> SQLAgent:
    """Create DB / vector store if missing, then load the agent."""
    if not os.path.exists(DB_PATH):
        build_database()
    from vector_store import VectorStore

    if not VectorStore.is_ready():
        build_vector_store(DB_PATH)
    auth.init_db()
    return SQLAgent()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _agent
    _agent = ensure_ready()
    yield
    _agent = None


app = FastAPI(
    title="AI Agent Analytics Assistant",
    description="Natural language → SQL → results",
    lifespan=lifespan,
)

# Same-origin nginx proxy needs no CORS; set ALLOWED_ORIGINS for split dev/prod hosts.
_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_extra = os.getenv("ALLOWED_ORIGINS", "")
_cors_origins = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Authentication ─────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """Resolve the signed-in account, or reject the request."""
    token = credentials.credentials if credentials else ""
    user = auth.user_for_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    return user


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(body: SignupRequest) -> AuthResponse:
    try:
        user = auth.create_user(body.name, body.email, body.password)
    except auth.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Give the new account its own orders and reviews so it can query itself
    provision_customer(user["name"], user["email"])
    return AuthResponse(token=auth.create_session(user["id"]), user=UserOut(**user))


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    try:
        user = auth.authenticate(body.email, body.password)
    except auth.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    # Re-create the profile if the business database was rebuilt since signup
    provision_customer(user["name"], user["email"])
    return AuthResponse(token=auth.create_session(user["id"]), user=UserOut(**user))


@app.post("/api/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, bool]:
    if credentials:
        auth.delete_session(credentials.credentials)
    return {"ok": True}


@app.get("/api/auth/me", response_model=UserOut)
def me(user: dict[str, Any] = Depends(current_user)) -> UserOut:
    return UserOut(**user)


# ── App data ───────────────────────────────────────────────────────


@app.get("/api/health")
def health() -> dict[str, str]:
    has_key = bool(os.getenv("GROQ_API_KEY"))
    return {
        "status": "ok" if has_key else "missing_api_key",
        "model": get_agent().model,
        "provider": "groq",
    }


@app.get("/api/examples")
def examples(_: dict[str, Any] = Depends(current_user)) -> dict[str, list[str]]:
    return {"examples": EXAMPLE_QUESTIONS}


@app.get("/api/schema")
def schema(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    """Return table / column metadata for the Explore page."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database not found")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    tables = []
    for (name,) in cur.fetchall():
        cur.execute(f"PRAGMA table_info({name})")
        columns = [
            {
                "name": col[1],
                "type": col[2] or "ANY",
                "notnull": bool(col[3]),
                "pk": bool(col[5]),
            }
            for col in cur.fetchall()
        ]
        cur.execute(f"SELECT COUNT(*) FROM {name}")
        row_count = cur.fetchone()[0]
        tables.append({"name": name, "columns": columns, "row_count": row_count})
    conn.close()
    return {"tables": tables}


def _is_id_column(name: str) -> bool:
    """Hide primary/foreign key style columns from API responses."""
    n = (name or "").strip().lower()
    return n == "id" or n.endswith("_id")


def _strip_id_columns(
    columns: list[str], rows: list[list[Any]]
) -> tuple[list[str], list[list[Any]]]:
    keep = [i for i, col in enumerate(columns) if not _is_id_column(col)]
    if len(keep) == len(columns):
        return columns, rows
    safe_cols = [columns[i] for i in keep]
    safe_rows = [[row[i] for i in keep] for row in rows]
    return safe_cols, safe_rows


@app.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest, user: dict[str, Any] = Depends(current_user)) -> AskResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = get_agent().ask(
            question,
            user_id=str(user["id"]),
            identity={"name": user["name"], "email": user["email"]},
        )
    except Exception as exc:
        # Surface LLM / API failures cleanly to the frontend
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    columns, rows = _strip_id_columns(result["columns"], result["rows"])
    # Cap payload size so huge result sets don't freeze the browser
    max_rows = 200
    truncated = rows[:max_rows]

    auth.record_question(
        user_id=user["id"],
        question=result["question"],
        row_count=len(rows),
        succeeded=result["error"] is None,
    )

    return AskResponse(
        question=result["question"],
        sql=result["sql"],
        columns=columns,
        rows=truncated,
        row_count=len(rows),
        error=result["error"],
        blocked=bool(result.get("blocked")),
    )


@app.get("/api/history", response_model=list[HistoryItem])
def history(user: dict[str, Any] = Depends(current_user)) -> list[HistoryItem]:
    return [HistoryItem(**item) for item in auth.list_history(user["id"])]


@app.delete("/api/history")
def delete_history(user: dict[str, Any] = Depends(current_user)) -> dict[str, bool]:
    auth.clear_history(user["id"])
    return {"ok": True}
