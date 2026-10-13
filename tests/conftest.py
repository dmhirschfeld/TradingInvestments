"""Each test gets its own throwaway Postgres schema in the test database, dropped afterwards."""

import uuid

import pytest

from trading import db

TEST_URL = "postgresql:///trading_test"   # local test database, see docs/infrastructure.md


@pytest.fixture
def conn():
    c = db.connect(TEST_URL)
    schema = f"t_{uuid.uuid4().hex[:12]}"
    c.execute(f"CREATE SCHEMA {schema}")
    c.execute(f"SET search_path TO {schema}")
    db.migrate(c)
    try:
        yield c
    finally:
        c.execute(f"DROP SCHEMA {schema} CASCADE")
        c.close()
