"""
User accounts, sessions, and per-user query history.

Kept in its own SQLite file (`accounts.db`) so the business dataset the agent
queries stays completely separate from application/user data.

Passwords use PBKDF2-HMAC-SHA256 with a per-user salt (stdlib only).
Sessions are opaque random tokens stored server-side so they can be revoked.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

AUTH_DB_PATH = os.path.join(os.path.dirname(__file__), "accounts.db")

PBKDF2_ITERATIONS = 200_000
SESSION_TTL_DAYS = 7

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS query_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    question   TEXT NOT NULL,
    row_count  INTEGER NOT NULL DEFAULT 0,
    succeeded  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_user ON query_history(user_id, history_id DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""


class AuthError(Exception):
    """Raised for signup/login problems that should surface to the client."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _connect(db_path: str = AUTH_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = AUTH_DB_PATH) -> None:
    """Create the accounts database if it does not exist yet."""
    conn = _connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


# ── Password hashing ───────────────────────────────────────────────

def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return digest.hex(), salt


def _verify_password(password: str, password_hash: str, salt: str) -> bool:
    candidate, _ = _hash_password(password, salt)
    # constant-time compare to avoid leaking hash prefixes via timing
    return hmac.compare_digest(candidate, password_hash)


# ── Accounts ───────────────────────────────────────────────────────

def _public_user(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["user_id"], "name": row["name"], "email": row["email"]}


def create_user(name: str, email: str, password: str) -> dict[str, Any]:
    name = name.strip()
    email = email.strip().lower()

    if not name:
        raise AuthError("Please enter your name")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise AuthError("Please enter a valid email address")
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters")

    password_hash, salt = _hash_password(password)

    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, password_salt, created_at)"
            " VALUES (?,?,?,?,?)",
            (name, email, password_hash, salt, _iso(_now())),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (cur.lastrowid,)
        ).fetchone()
        return _public_user(row)
    except sqlite3.IntegrityError as exc:
        raise AuthError("An account with that email already exists") from exc
    finally:
        conn.close()


def authenticate(email: str, password: str) -> dict[str, Any]:
    email = email.strip().lower()
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()

    if row is None or not _verify_password(password, row["password_hash"], row["password_salt"]):
        # Same message either way so accounts can't be enumerated
        raise AuthError("Incorrect email or password")

    return _public_user(row)


# ── Sessions ───────────────────────────────────────────────────────

def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?,?,?,?)",
            (token, user_id, _iso(now), _iso(now + timedelta(days=SESSION_TTL_DAYS))),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def user_for_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT u.*, s.expires_at FROM sessions s"
            " JOIN users u ON u.user_id = s.user_id"
            " WHERE s.token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        if datetime.fromisoformat(row["expires_at"]) < _now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        return _public_user(row)
    finally:
        conn.close()


def delete_session(token: str) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


# ── Per-user question history ──────────────────────────────────────

def record_question(user_id: int, question: str, row_count: int, succeeded: bool) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO query_history (user_id, question, row_count, succeeded, created_at)"
            " VALUES (?,?,?,?,?)",
            (user_id, question, row_count, 1 if succeeded else 0, _iso(_now())),
        )
        conn.commit()
    finally:
        conn.close()


def list_history(user_id: int, limit: int = 100) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT history_id, question, row_count, succeeded, created_at"
            " FROM query_history WHERE user_id = ?"
            " ORDER BY history_id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "id": r["history_id"],
            "question": r["question"],
            "row_count": r["row_count"],
            "succeeded": bool(r["succeeded"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def clear_history(user_id: int) -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM query_history WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
