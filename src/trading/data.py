"""Market data: provider adapters (DR1), point-in-time storage (FR1.1) and quality checks (FR1.3)."""

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol

import psycopg

from trading import raw_store


@dataclass(frozen=True)
class Bar:
    symbol: str
    day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class BarSource(Protocol):
    name: str

    def fetch_daily_bars(self, day: date) -> tuple[str, str]:
        """Return (request description, raw response body) for one trading day."""

    def parse(self, body: str) -> list[Bar]: ...


class FixtureSource:
    """Recorded sample data, used until provider accounts exist.
    File shape: {"YYYY-MM-DD": [{"symbol", "open", "high", "low", "close", "volume"}, ...]}."""

    name = "fixture"

    def __init__(self, path: Path):
        self._days = json.loads(Path(path).read_text())

    def fetch_daily_bars(self, day: date) -> tuple[str, str]:
        key = day.isoformat()
        if key not in self._days:
            raise LookupError(f"fixture has no bars for {key}")
        return f"fixture:{key}", json.dumps({"day": key, "bars": self._days[key]})

    def parse(self, body: str) -> list[Bar]:
        doc = json.loads(body)
        d = date.fromisoformat(doc["day"])
        return [Bar(b["symbol"], d, Decimal(str(b["open"])), Decimal(str(b["high"])),
                    Decimal(str(b["low"])), Decimal(str(b["close"])), int(b["volume"]))
                for b in doc["bars"]]


def ingest(conn: psycopg.Connection, source: BarSource, day: date, known_at: datetime) -> list[Bar]:
    """Save the raw answer first, then the parsed bars stamped with when we learned them."""
    request, body = source.fetch_daily_bars(day)
    raw_id = raw_store.save(conn, source.name, request, body)
    bars = source.parse(body)
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO daily_bars (symbol, day, open, high, low, close, volume, known_at, source, raw_id)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (symbol, day, known_at, source) DO NOTHING",
            [(b.symbol, b.day, b.open, b.high, b.low, b.close, b.volume, known_at, source.name, raw_id)
             for b in bars],
        )
    return bars


def closes_as_of(conn: psycopg.Connection, as_of: datetime) -> dict[str, list[Decimal]]:
    """Closing prices per symbol, oldest first, using only what was known at `as_of`."""
    rows = conn.execute(
        "SELECT DISTINCT ON (symbol, day) symbol, day, close FROM daily_bars"
        " WHERE known_at <= %s ORDER BY symbol, day, known_at DESC",
        (as_of,),
    ).fetchall()
    out: dict[str, list[Decimal]] = {}
    for sym, _day, close in rows:
        out.setdefault(sym, []).append(close)
    return out


def bars_for_day(conn: psycopg.Connection, day: date, as_of: datetime) -> dict[str, Bar]:
    rows = conn.execute(
        "SELECT DISTINCT ON (symbol) symbol, day, open, high, low, close, volume FROM daily_bars"
        " WHERE day = %s AND known_at <= %s ORDER BY symbol, known_at DESC",
        (day, as_of),
    ).fetchall()
    return {r[0]: Bar(*r) for r in rows}


def avg_dollar_volume(conn: psycopg.Connection, symbol: str, as_of: datetime,
                      days: int = 20) -> Decimal:
    row = conn.execute(
        "SELECT AVG(close * volume) FROM ("
        " SELECT DISTINCT ON (day) day, close, volume FROM daily_bars"
        " WHERE symbol = %s AND known_at <= %s ORDER BY day DESC, known_at DESC LIMIT %s) t",
        (symbol, as_of, days),
    ).fetchone()
    return row[0] or Decimal(0)


MAX_DAILY_MOVE = Decimal("0.5")   # a 50% one-day move is treated as a possible unadjusted split


def quality_problems(bars: list[Bar], expected: set[str],
                     prior_close: dict[str, Decimal]) -> list[str]:
    """Empty list means the day passes. Any problem blocks trading for the day (RM3)."""
    problems = []
    seen = {b.symbol for b in bars}
    for sym in sorted(expected - seen):
        problems.append(f"{sym}: missing bar")
    for b in bars:
        if min(b.open, b.high, b.low, b.close) <= 0:
            problems.append(f"{b.symbol}: non-positive price")
        elif b.high < max(b.open, b.close, b.low) or b.low > min(b.open, b.close):
            problems.append(f"{b.symbol}: high/low inconsistent")
        prev = prior_close.get(b.symbol)
        if prev and abs(b.close / prev - 1) >= MAX_DAILY_MOVE:
            problems.append(f"{b.symbol}: {b.close / prev - 1:.0%} move, possible split")
        if prev is not None and b.close == prev and b.volume == 0:
            problems.append(f"{b.symbol}: stale price")
    return problems
