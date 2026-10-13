"""Append-only audit log with a hash chain (FR11). Any edit breaks the chain."""

import hashlib
import json
from datetime import date

import psycopg

GENESIS = "genesis"
_LOCK_KEY = 7_311_001  # serializes appends so the chain stays linear


def _digest(prev_hash: str, step: str, kind: str, payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(f"{prev_hash}|{step}|{kind}|{body}".encode()).hexdigest()


def append(conn: psycopg.Connection, step: str, kind: str, payload: dict,
           run_day: date | None = None) -> str:
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK_KEY,))
        row = conn.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        prev = row[0] if row else GENESIS
        h = _digest(prev, step, kind, payload)
        conn.execute(
            "INSERT INTO audit_log (run_day, step, kind, payload, prev_hash, hash)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (run_day, step, kind, json.dumps(payload, sort_keys=True, default=str), prev, h),
        )
    return h


def verify(conn: psycopg.Connection) -> None:
    """Raise if any row was altered or the chain is broken."""
    prev = GENESIS
    for rid, step, kind, payload, prev_hash, h in conn.execute(
        "SELECT id, step, kind, payload, prev_hash, hash FROM audit_log ORDER BY id"
    ):
        if prev_hash != prev or _digest(prev, step, kind, payload) != h:
            raise RuntimeError(f"audit chain broken at row {rid}")
        prev = h
