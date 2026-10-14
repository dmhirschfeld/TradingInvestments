"""Daily ledger-vs-broker check (FR8.2). Any mismatch halts trading."""

from decimal import Decimal

import psycopg

from trading import ledger
from trading.broker import Broker

TOLERANCE = Decimal("0.000001")


class ReconciliationError(RuntimeError):
    pass


def check(conn: psycopg.Connection, portfolio_id: int, broker: Broker) -> None:
    ours = ledger.positions(conn, portfolio_id)
    theirs = broker.positions()
    diffs = {
        sym: (ours.get(sym, Decimal(0)), theirs.get(sym, Decimal(0)))
        for sym in set(ours) | set(theirs)
        if abs(ours.get(sym, Decimal(0)) - theirs.get(sym, Decimal(0))) > TOLERANCE
    }
    if diffs:
        raise ReconciliationError(f"portfolio {portfolio_id} ledger vs broker: {diffs}")
