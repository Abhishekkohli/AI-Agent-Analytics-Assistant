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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from setup_database import DB_PATH, build_database
from sql_agent import SQLAgent
from vector_store import build_vector_store


# Example prompts shown in the UI — cover common analytics patterns
EXAMPLE_QUESTIONS = [
    "What are the top 5 products by total revenue?",
    "How many orders were placed in each city?",
    "Which customers have spent more than $500?",
    "What is the average product rating by category?",
    "Show monthly order totals for the last year",
    "Which products have fewer than 20 units in stock?",
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    has_key = bool(os.getenv("GROQ_API_KEY"))
    return {
        "status": "ok" if has_key else "missing_api_key",
        "model": get_agent().model,
        "provider": "groq",
    }


@app.get("/api/examples")
def examples() -> dict[str, list[str]]:
    return {"examples": EXAMPLE_QUESTIONS}


@app.get("/api/schema")
def schema() -> dict[str, Any]:
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


@app.post("/api/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = get_agent().ask(question)
    except Exception as exc:
        # Surface LLM / API failures cleanly to the frontend
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    rows = result["rows"]
    # Cap payload size so huge result sets don't freeze the browser
    max_rows = 200
    truncated = rows[:max_rows]

    return AskResponse(
        question=result["question"],
        sql=result["sql"],
        columns=result["columns"],
        rows=truncated,
        row_count=len(rows),
        error=result["error"],
    )
