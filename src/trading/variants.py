"""Pipeline definitions (FR15). Each pipeline runs once per account size."""

from dataclasses import dataclass
from decimal import Decimal

import psycopg

from trading.constants import ACCOUNT_SIZES


@dataclass(frozen=True)
class Pipeline:
    key: str
    description: str
    active_from_phase: int
    mirror_account: str | None = None   # Alpaca paper account label, $5,000 set only
    risk_gate: bool = True              # buy-and-hold yardsticks and the no-check test skip it


PIPELINES = (
    Pipeline("spy_hold", "Buy and hold SPY", 1, risk_gate=False),
    Pipeline("iwm_hold", "Buy and hold IWM", 1, risk_gate=False),
    Pipeline("momentum", "12-1 month momentum, equal weight", 1, "alpaca_paper_1"),
    Pipeline("random_entry", "Random picks from the shortlist, same sizing and risk", 2),
    Pipeline("llm_off", "Shortlist with screener-quintile conviction, no Claude", 2),
    Pipeline("claude_formula", "Claude picks, formula sizes, risk gate on", 4, "alpaca_paper_2"),
    Pipeline("claude_sizes", "Claude picks and sizes, risk gate on", 4, "alpaca_paper_3"),
    Pipeline("claude_no_gate", "Claude picks and sizes, no risk gate (paper only)", 4, risk_gate=False),
    Pipeline("claude_themes", "Claude formula-sized, themes as reasoning", 4),
    Pipeline("claude_themes_tilt", "Claude formula-sized, themes with automatic tilt", 4),
    Pipeline("claude_candles", "Claude formula-sized, candlestick patterns included", 4),
)


BY_KEY = {p.key: p for p in PIPELINES}


def portfolio_name(pipeline_key: str, size: int) -> str:
    return f"{pipeline_key}_{size}"


def seed(conn: psycopg.Connection) -> int:
    """Create every pipeline x size portfolio that does not exist yet. Returns how many were created."""
    created = 0
    for p in PIPELINES:
        for size in ACCOUNT_SIZES:
            mirror = p.mirror_account if size == min(ACCOUNT_SIZES) else None
            row = conn.execute(
                "INSERT INTO portfolios (name, pipeline, starting_cash, mirror_account)"
                " VALUES (%s, %s, %s, %s) ON CONFLICT (name) DO NOTHING RETURNING id",
                (portfolio_name(p.key, size), p.key, Decimal(size), mirror),
            ).fetchone()
            created += row is not None
    return created
