"""Postgres connection and migrations."""

import os
from pathlib import Path

import psycopg

MIGRATIONS = Path(__file__).parent / "migrations"


def database_url() -> str:
    url = os.environ.get("TRADING_DATABASE_URL")
    if not url:
        raise RuntimeError("TRADING_DATABASE_URL is not set")
    return url


def connect(url: str | None = None) -> psycopg.Connection:
    # Autocommit, so each `conn.transaction()` block is a real, committed transaction.
    return psycopg.connect(url or database_url(), autocommit=True)


def migrate(conn: psycopg.Connection) -> list[str]:
    """Apply every migration not yet recorded. Returns the names applied."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if path.name in done:
            continue
        with conn.transaction():
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
        applied.append(path.name)
    return applied
