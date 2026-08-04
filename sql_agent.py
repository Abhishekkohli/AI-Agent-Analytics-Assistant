"""
LLM-powered SQL generation agent.

Pipeline:
  user question ─► context_manager (vector retrieval) ─► LLM ─► SQL
  SQL ─► SQLite execution ─► formatted results
  successful pair ─► fed back into vector store for future retrieval
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Any

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

from context_manager import ContextManager
from vector_store import VectorStore, build_vector_store
from setup_database import DB_PATH

load_dotenv()

# Groq free-tier models (OpenAI-compatible API)
DEFAULT_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Phrases that name a row count ("top 5", "last 3 orders", "3 most recent").
# The lookahead keeps time windows such as "last 3 months" out of the match.
ROW_COUNT_PATTERNS = (
    re.compile(
        r"\b(?:top|bottom|first|last|latest|newest|oldest|recent)\s+(\d{1,4})\b"
        r"(?!\s*(?:day|week|month|year|hour|minute|quarter)s?\b)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d{1,4})\s+(?:most\s+\w+|best[- ]selling|top|highest|lowest|"
        r"largest|smallest|biggest|latest|newest|oldest|recent)\b",
        re.IGNORECASE,
    ),
)

# Columns that identify an individual shopper. Anything sourced from these is
# private unless the query is restricted to the signed-in account.
IDENTITY_COLUMNS = re.compile(
    r"\b(first_name|last_name|full_name|customer_name|email|phone)\b", re.IGNORECASE
)
SQL_STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")
EMAIL_VALUE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PRIVACY_MESSAGE = (
    "For privacy, I can only show personal details for your own account. "
    "Try asking about your own orders, or about the store as a whole."
)


class SQLAgent:
    """End-to-end NL → SQL → results agent."""

    def __init__(
        self,
        db_path: str = DB_PATH,
        model: str = DEFAULT_MODEL,
        verbose: bool = False,
    ):
        self.db_path = db_path
        self.model = model
        self.verbose = verbose
        # Lazy client so the API can boot without a key (ask() fails clearly later)
        self._client: OpenAI | None = None

        # Load Chroma vector DB, or build schema + seed history on first run
        if VectorStore.is_ready():
            self.store = VectorStore()
        else:
            self.store = build_vector_store(db_path)

        self.ctx = ContextManager(self.store, relationships=self._load_relationships())

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "Missing GROQ_API_KEY. Get a free key at https://console.groq.com/keys "
                    "and add it to your .env file."
                )
            # Same OpenAI SDK, pointed at Groq's compatible endpoint
            self._client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        return self._client

    # ── Public API ─────────────────────────────────────────────────

    def ask(
        self,
        question: str,
        user_id: str | None = None,
        identity: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Full pipeline: question → SQL → execute → result dict.
        `user_id` keeps retrieved examples and stored history per account, and
        `identity` ({"name", "email"}) resolves first-person questions.
        Returns:
          {
            "question": str,
            "sql": str,
            "columns": list[str],
            "rows": list[tuple],
            "dataframe": pd.DataFrame,
            "error": str | None,
          }
        """
        messages = self.ctx.build_prompt(question, user_id, identity)

        if self.verbose:
            print(f"\n[Context] System prompt length: {len(messages[0]['content'])} chars")

        sql = self._call_llm(messages)
        sql = self._clean_sql(sql)
        sql = self._apply_row_limit(question, sql)

        if self.verbose:
            print(f"[SQL] {sql}")

        if self._violates_privacy(sql, identity):
            return {
                "question": question,
                "sql": sql,
                "columns": [],
                "rows": [],
                "dataframe": pd.DataFrame(),
                "error": PRIVACY_MESSAGE,
                "blocked": True,
            }

        result = self._execute(sql)

        # One repair attempt: hand the database error back to the model
        if result["error"] is not None:
            repaired = self._repair_sql(messages, sql, result["error"])
            if repaired and repaired != sql:
                repaired = self._apply_row_limit(question, repaired)
                retry = self._execute(repaired)
                if retry["error"] is None:
                    if self.verbose:
                        print(f"[SQL repaired] {repaired}")
                    sql, result = repaired, retry

        # Last line of defence: never hand back someone else's email address
        if result["error"] is None and self._leaks_other_people(result["rows"], identity):
            return {
                "question": question,
                "sql": sql,
                "columns": [],
                "rows": [],
                "dataframe": pd.DataFrame(),
                "error": PRIVACY_MESSAGE,
                "blocked": True,
            }

        result["question"] = question
        result["sql"] = sql
        result["blocked"] = False

        # Feed successful queries back into the store for future retrieval
        if result["error"] is None:
            self.ctx.add_to_history(question, sql, user_id)

        return result

    def ask_text(self, question: str) -> str:
        """Convenience wrapper that returns a formatted text answer."""
        r = self.ask(question)
        if r["error"]:
            return f"SQL:\n  {r['sql']}\n\nError: {r['error']}"
        df = r["dataframe"]
        table_str = df.to_string(index=False) if len(df) <= 50 else df.head(30).to_string(index=False) + "\n... (truncated)"
        return f"SQL:\n  {r['sql']}\n\nResults ({len(df)} rows):\n{table_str}"

    # ── Internals ──────────────────────────────────────────────────

    def _call_llm(self, messages: list[dict]) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.0,
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()

    @staticmethod
    def _clean_sql(raw: str) -> str:
        """Strip markdown fences and trailing semicolons."""
        cleaned = re.sub(r"```(?:sql)?\s*", "", raw)
        cleaned = cleaned.strip().rstrip(";")
        return cleaned

    @staticmethod
    def _requested_row_count(question: str) -> int | None:
        for pattern in ROW_COUNT_PATTERNS:
            match = pattern.search(question)
            if match:
                count = int(match.group(1))
                if count > 0:
                    return count
        return None

    @classmethod
    def _apply_row_limit(cls, question: str, sql: str) -> str:
        """
        Safety net for when the model ignores an explicit row count. Only fires
        if the question names one and the generated SQL has no LIMIT of its own.
        """
        count = cls._requested_row_count(question)
        if count is None or re.search(r"\blimit\b", sql, re.IGNORECASE):
            return sql
        return f"{sql} LIMIT {count}"

    @staticmethod
    def _violates_privacy(sql: str, identity: dict[str, Any] | None) -> bool:
        """
        Allow store-wide aggregates, but refuse anything that exposes an
        individual shopper other than the person asking.

        A query is fine when it never touches `customers`, or when it touches
        it without surfacing identity columns (e.g. counting orders per city).
        Once identity columns are involved, the query must be pinned to the
        signed-in email.
        """
        if not identity or not identity.get("email"):
            return False

        lowered = sql.lower()
        if not re.search(r"\bcustomers\b", lowered):
            return False

        # Blank out literals first so customer data inside strings can't
        # masquerade as a column name
        body = SQL_STRING_LITERAL.sub("''", lowered)
        if not IDENTITY_COLUMNS.search(body):
            return False

        return str(identity["email"]).lower() not in lowered

    @staticmethod
    def _leaks_other_people(rows: list, identity: dict[str, Any] | None) -> bool:
        if not identity or not identity.get("email"):
            return False
        mine = str(identity["email"]).strip().lower()
        for row in rows:
            for cell in row:
                if isinstance(cell, str):
                    value = cell.strip().lower()
                    if EMAIL_VALUE.match(value) and value != mine:
                        return True
        return False

    def _load_relationships(self) -> str:
        """Read every foreign key so the prompt always shows valid join paths."""
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            tables = [
                row[0]
                for row in cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                    " AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            lines = []
            for table in tables:
                for fk in cur.execute(f"PRAGMA foreign_key_list({table})").fetchall():
                    _, _, ref_table, from_col, to_col = fk[:5]
                    lines.append(f"- {table}.{from_col} -> {ref_table}.{to_col}")
            conn.close()
            return "\n".join(lines)
        except Exception:
            return ""

    def _repair_sql(self, messages: list[dict], sql: str, error: str) -> str | None:
        """Show the model its own failing query plus the error and ask for a fix."""
        followup = messages + [
            {"role": "assistant", "content": sql},
            {
                "role": "user",
                "content": (
                    f"That query failed with this database error:\n{error}\n\n"
                    "Rewrite it as valid SQLite using only the tables, columns, and "
                    "relationships listed above. Output ONLY the corrected SQL."
                ),
            },
        ]
        try:
            return self._clean_sql(self._call_llm(followup))
        except Exception:
            return None

    def _execute(self, sql: str) -> dict[str, Any]:
        """Run SQL against SQLite and return columns + rows."""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(sql, conn)
            conn.close()
            return {
                "columns": list(df.columns),
                "rows": df.values.tolist(),
                "dataframe": df,
                "error": None,
            }
        except Exception as e:
            return {
                "columns": [],
                "rows": [],
                "dataframe": pd.DataFrame(),
                "error": str(e),
            }
