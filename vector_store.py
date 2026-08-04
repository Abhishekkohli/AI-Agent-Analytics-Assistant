"""
ChromaDB-backed vector store for embedding-based retrieval.

Collection schema (`retrieval_docs`):
  - id          : string primary key
  - document    : text that is embedded (schema blurb or Q→SQL pair)
  - embedding   : vector (auto-generated via sentence-transformers)
  - metadata    :
      doc_type  : "schema" | "history"
      table     : table name (schema docs)
      question  : natural-language question (history docs)
      sql       : SQL string (history docs)

Unlike FAISS, Chroma stores vectors + documents + metadata together.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

STORE_DIR = os.path.join(os.path.dirname(__file__), ".chroma")
COLLECTION_NAME = "retrieval_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dim, local, no API key


def _embedding_fn() -> SentenceTransformerEmbeddingFunction:
    return SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)


class VectorStore:
    """Persistent Chroma collection for schema + query-history retrieval."""

    def __init__(self, persist_dir: str = STORE_DIR):
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_embedding_fn(),
            metadata={
                "hnsw:space": "cosine",
                "description": "Schema descriptions and NL→SQL few-shot history",
            },
        )

    # ── Write ──────────────────────────────────────────────────────

    def add_documents(self, docs: list[dict[str, Any]]) -> None:
        """
        Upsert documents into Chroma.

        Each doc dict should have:
          - 'text': string to embed
          - 'type': 'schema' | 'history'
          - 'metadata': arbitrary dict (table name, SQL, etc.)
        """
        if not docs:
            return

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for doc in docs:
            doc_type = doc["type"]
            meta_in = doc.get("metadata") or {}
            # Chroma metadata values must be str/int/float/bool
            meta: dict[str, Any] = {"doc_type": doc_type}
            if doc_type == "schema":
                meta["table"] = str(meta_in.get("table", ""))
                meta["question"] = ""
                meta["sql"] = ""
                doc_id = f"schema::{meta['table']}" if meta["table"] else f"schema::{uuid.uuid4().hex}"
            else:
                question = str(meta_in.get("question", ""))
                sql = str(meta_in.get("sql", ""))
                meta["table"] = ""
                meta["question"] = question
                meta["sql"] = sql
                # Stable-ish id for seeds; unique id for runtime feedback
                doc_id = meta_in.get("id") or f"history::{uuid.uuid4().hex}"

            ids.append(str(doc_id))
            documents.append(doc["text"])
            metadatas.append(meta)

        # upsert so re-running setup refreshes schema docs cleanly
        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def clear(self) -> None:
        """Drop and recreate the collection (used by full rebuild)."""
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_embedding_fn(),
            metadata={
                "hnsw:space": "cosine",
                "description": "Schema descriptions and NL→SQL few-shot history",
            },
        )

    # ── Retrieve ───────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return the top-k most relevant documents for `query`.
        Optionally filter by doc_type ('schema' or 'history').
        """
        if self.collection.count() == 0:
            return []

        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": min(top_k, self.collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if doc_type:
            kwargs["where"] = {"doc_type": doc_type}

        raw = self.collection.query(**kwargs)
        results: list[dict[str, Any]] = []

        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]

        for text, meta, dist in zip(docs, metas, dists):
            meta = meta or {}
            # cosine distance → similarity-like score for callers
            score = 1.0 - float(dist) if dist is not None else 0.0
            results.append(
                {
                    "text": text or "",
                    "type": meta.get("doc_type", doc_type or ""),
                    "metadata": {
                        "table": meta.get("table", ""),
                        "question": meta.get("question", ""),
                        "sql": meta.get("sql", ""),
                    },
                    "score": score,
                }
            )
        return results

    # ── Introspection ──────────────────────────────────────────────

    def count(self) -> int:
        return self.collection.count()

    @staticmethod
    def is_ready(persist_dir: str = STORE_DIR) -> bool:
        """True when a persisted Chroma store already has documents."""
        if not os.path.isdir(persist_dir):
            return False
        try:
            store = VectorStore(persist_dir=persist_dir)
            return store.count() > 0
        except Exception:
            return False


# ── Helper: build schema docs from a live SQLite connection ────────

def schema_docs_from_db(db_path: str) -> list[dict]:
    """
    Introspect the SQLite database and produce one document per table
    describing its columns, types, and foreign keys.
    """
    import sqlite3

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]

    docs = []
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()
        cur.execute(f"PRAGMA foreign_key_list({table})")
        fks = cur.fetchall()

        col_lines = []
        for _, name, ctype, notnull, default, pk in cols:
            parts = [f"{name} {ctype}"]
            if pk:
                parts.append("PRIMARY KEY")
            if notnull:
                parts.append("NOT NULL")
            col_lines.append(", ".join(parts))

        fk_lines = []
        for fk in fks:
            fk_lines.append(f"  FK: {fk[3]} -> {fk[2]}({fk[4]})")

        description = f"Table: {table}\nColumns:\n  " + "\n  ".join(col_lines)
        if fk_lines:
            description += "\nForeign keys:\n" + "\n".join(fk_lines)

        cur.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cur.fetchone()[0]
        description += f"\nRow count: {row_count}"

        docs.append({
            "text": description,
            "type": "schema",
            "metadata": {"table": table},
        })

    conn.close()
    return docs


# ── Helper: build query-history docs ──────────────────────────────

SEED_QUERY_HISTORY = [
    {
        "question": "What are the top 5 best-selling products by revenue?",
        "sql": (
            "SELECT p.product_name, SUM(oi.line_total) AS revenue "
            "FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
            "GROUP BY p.product_name ORDER BY revenue DESC LIMIT 5;"
        ),
    },
    {
        "question": "How many orders were placed each month in 2025?",
        "sql": (
            "SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) AS order_count "
            "FROM orders WHERE order_date >= '2025-01-01' "
            "GROUP BY month ORDER BY month;"
        ),
    },
    {
        "question": "Which customers have spent more than $500 in total?",
        "sql": (
            "SELECT c.first_name || ' ' || c.last_name AS customer, "
            "SUM(o.total_amount) AS total_spent "
            "FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
            "WHERE o.status != 'cancelled' "
            "GROUP BY c.customer_id HAVING total_spent > 500 "
            "ORDER BY total_spent DESC;"
        ),
    },
    {
        "question": "What is the average product rating by category?",
        "sql": (
            "SELECT cat.category_name, ROUND(AVG(r.rating), 2) AS avg_rating "
            "FROM reviews r "
            "JOIN products p ON r.product_id = p.product_id "
            "JOIN categories cat ON p.category_id = cat.category_id "
            "GROUP BY cat.category_name ORDER BY avg_rating DESC;"
        ),
    },
    {
        "question": "Show the cancellation rate per month.",
        "sql": (
            "SELECT strftime('%Y-%m', order_date) AS month, "
            "ROUND(100.0 * SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) "
            "/ COUNT(*), 1) AS cancel_pct "
            "FROM orders GROUP BY month ORDER BY month;"
        ),
    },
    {
        "question": "Which state has the most customers?",
        "sql": (
            "SELECT state, COUNT(*) AS customer_count "
            "FROM customers GROUP BY state ORDER BY customer_count DESC LIMIT 1;"
        ),
    },
    {
        "question": "List products that have never been ordered.",
        "sql": (
            "SELECT p.product_name FROM products p "
            "LEFT JOIN order_items oi ON p.product_id = oi.product_id "
            "WHERE oi.item_id IS NULL;"
        ),
    },
    {
        "question": "What is the total revenue by department?",
        "sql": (
            "SELECT cat.department, SUM(oi.line_total) AS revenue "
            "FROM order_items oi "
            "JOIN products p ON oi.product_id = p.product_id "
            "JOIN categories cat ON p.category_id = cat.category_id "
            "GROUP BY cat.department ORDER BY revenue DESC;"
        ),
    },
    {
        "question": "Who are the top 3 customers by number of orders?",
        "sql": (
            "SELECT c.first_name || ' ' || c.last_name AS customer, "
            "COUNT(o.order_id) AS num_orders "
            "FROM orders o JOIN customers c ON o.customer_id = c.customer_id "
            "GROUP BY c.customer_id ORDER BY num_orders DESC LIMIT 3;"
        ),
    },
    {
        "question": "What is the average order value for delivered orders?",
        "sql": (
            "SELECT ROUND(AVG(total_amount), 2) AS avg_order_value "
            "FROM orders WHERE status = 'delivered';"
        ),
    },
]


def history_docs() -> list[dict]:
    """Convert seed query history into embeddable documents."""
    docs = []
    for i, pair in enumerate(SEED_QUERY_HISTORY):
        text = f"Question: {pair['question']}\nSQL: {pair['sql']}"
        docs.append({
            "text": text,
            "type": "history",
            "metadata": {
                "id": f"history::seed::{i}",
                "question": pair["question"],
                "sql": pair["sql"],
            },
        })
    return docs


def build_vector_store(db_path: str) -> VectorStore:
    """One-call helper: rebuild & persist the Chroma collection from scratch."""
    store = VectorStore()
    store.clear()
    store.add_documents(schema_docs_from_db(db_path))
    store.add_documents(history_docs())
    print(f"Chroma vector store built — {store.count()} documents in '{COLLECTION_NAME}'")
    return store
