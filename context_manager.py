"""
Context management pipeline for the SQL generation agent.

Given a user's natural-language question, this module:
  1. Retrieves the most relevant table schemas via vector similarity
  2. Retrieves similar past (question → SQL) pairs as few-shot examples
  3. Assembles a structured prompt that maximises LLM accuracy
"""

from __future__ import annotations
from vector_store import VectorStore


SYSTEM_PROMPT = """\
You are an expert SQL analyst. You have access to a SQLite database with the
schema described below. Your job is to convert the user's natural-language
business question into a single, correct SQL query.

Rules:
- Output ONLY the SQL query, no explanations.
- Use SQLite-compatible syntax (e.g. strftime for dates).
- Do NOT use LIMIT unless the user explicitly asks for a specific count.
- Always qualify ambiguous column names with table aliases.
- Use JOINs, not sub-selects, when possible.
- Return readable column aliases (e.g. "total_revenue", not "SUM(oi.line_total)").
- NEVER select or return primary-key / foreign-key id columns
  (e.g. product_id, customer_id, order_id, category_id, review_id, item_id, or plain id).
  Prefer human-readable fields such as names, emails, dates, amounts, and statuses.
"""


class ContextManager:
    """Builds the LLM prompt by injecting retrieved schema + few-shot context."""

    def __init__(self, store: VectorStore, schema_top_k: int = 4, history_top_k: int = 3):
        self.store = store
        self.schema_top_k = schema_top_k
        self.history_top_k = history_top_k

    def build_prompt(
        self,
        user_question: str,
        user_id: str | None = None,
        identity: dict | None = None,
    ) -> list[dict]:
        """
        Returns an OpenAI-style messages list:
          [system, user]
        with retrieved context injected into the system message.

        `user_id` limits few-shot examples to shared seeds plus that account's
        own past questions. `identity` ({"name", "email"}) lets the model
        resolve first-person questions to that person's customer record.
        """
        schema_ctx = self._retrieve_schema(user_question)
        history_ctx = self._retrieve_history(user_question, user_id)
        system_msg = self._assemble_system(schema_ctx, history_ctx, identity)
        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_question},
        ]

    # ── Private helpers ────────────────────────────────────────────

    def _retrieve_schema(self, question: str) -> str:
        results = self.store.search(question, top_k=self.schema_top_k, doc_type="schema")
        if not results:
            return "No schema information retrieved."
        blocks = []
        for r in results:
            blocks.append(r["text"])
        return "\n\n".join(blocks)

    def _retrieve_history(self, question: str, user_id: str | None = None) -> str:
        results = self.store.search(
            question, top_k=self.history_top_k, doc_type="history", user_id=user_id
        )
        if not results:
            return ""
        lines = []
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            lines.append(f"Example {i}:")
            lines.append(f"  Q: {meta['question']}")
            lines.append(f"  SQL: {meta['sql']}")
        return "\n".join(lines)

    def _assemble_system(
        self, schema_ctx: str, history_ctx: str, identity: dict | None = None
    ) -> str:
        parts = [SYSTEM_PROMPT, "=== DATABASE SCHEMA ===", schema_ctx]
        if identity and identity.get("email"):
            parts.append(self._identity_block(identity))
        if history_ctx:
            parts.append("=== SIMILAR QUERY EXAMPLES ===")
            parts.append(history_ctx)
        return "\n\n".join(parts)

    @staticmethod
    def _identity_block(identity: dict) -> str:
        """Tell the model which customer row the asker is, so 'my orders' works."""
        email = str(identity.get("email", "")).replace("'", "''")
        name = identity.get("name", "")
        return (
            "=== WHO IS ASKING ===\n"
            f"The person asking is {name}, a customer in this database with\n"
            f"email '{email}'.\n"
            "When the question says I, me, my, or mine, restrict the query to that\n"
            f"customer using customers.email = '{email}'."
        )

    # ── Runtime history injection ──────────────────────────────────

    def add_to_history(self, question: str, sql: str, user_id: str | None = None) -> None:
        """
        Add a successful (question, SQL) pair to the vector DB at
        runtime so the agent improves as the session progresses.
        Chroma upserts embeddings + metadata together (no separate rebuild).

        The pair is tagged with the asking account so it is only retrieved for
        that user later.
        """
        doc = {
            "text": f"Question: {question}\nSQL: {sql}",
            "type": "history",
            "metadata": {
                "question": question,
                "sql": sql,
                "user_id": str(user_id or ""),
            },
        }
        self.store.add_documents([doc])
