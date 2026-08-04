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

        self.ctx = ContextManager(self.store)

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

        if self.verbose:
            print(f"[SQL] {sql}")

        result = self._execute(sql)
        result["question"] = question
        result["sql"] = sql

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
