"""Save every provider answer before it is parsed (DR2), so data can be reprocessed."""

import hashlib

import psycopg


def save(conn: psycopg.Connection, source: str, request: str, body: str) -> int:
    sha = hashlib.sha256(body.encode()).hexdigest()
    row = conn.execute(
        "INSERT INTO raw_responses (source, request, body, sha256) VALUES (%s, %s, %s, %s)"
        " RETURNING id",
        (source, request, body, sha),
    ).fetchone()
    return row[0]
