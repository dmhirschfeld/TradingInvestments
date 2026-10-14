"""Internal ledger: source of truth for every virtual portfolio (FR9.1).

Positions and cash are derived from fills, never stored separately, so they
cannot drift from the trade record.
"""

from decimal import Decimal

import psycopg

from trading.constants import BUY, SELL, normalize


def positions(conn: psycopg.Connection, portfolio_id: int) -> dict[str, Decimal]:
    rows = conn.execute(
        "SELECT o.symbol,"
        " SUM(CASE WHEN o.side = %s THEN f.qty ELSE -f.qty END)"
        " FROM fills f JOIN orders o ON o.id = f.order_id"
        " WHERE o.portfolio_id = %s GROUP BY o.symbol",
        (BUY, portfolio_id),
    ).fetchall()
    return {sym: qty for sym, qty in rows if qty != 0}


def cash(conn: psycopg.Connection, portfolio_id: int) -> Decimal:
    start = conn.execute(
        "SELECT starting_cash FROM portfolios WHERE id = %s", (portfolio_id,)
    ).fetchone()
    if start is None:
        raise LookupError(f"portfolio {portfolio_id} does not exist")
    spent = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN o.side = %s THEN f.qty * f.price + f.cost"
        "                         ELSE -(f.qty * f.price) + f.cost END), 0)"
        " FROM fills f JOIN orders o ON o.id = f.order_id WHERE o.portfolio_id = %s",
        (BUY, portfolio_id),
    ).fetchone()[0]
    return start[0] - spent


def record_fill(conn: psycopg.Connection, order_id: int, qty: Decimal, price: Decimal,
                cost: Decimal, source: str) -> int:
    order = conn.execute(
        "SELECT portfolio_id, symbol, side FROM orders WHERE id = %s", (order_id,)
    ).fetchone()
    if order is None:
        raise LookupError(f"order {order_id} does not exist")
    portfolio_id, symbol, side = order
    side = normalize(side)
    if side == SELL and positions(conn, portfolio_id).get(symbol, Decimal(0)) < qty:
        raise ValueError(f"sell of {qty} {symbol} exceeds the position held")
    if side == BUY and cash(conn, portfolio_id) < qty * price + cost:
        raise ValueError(f"buy of {qty} {symbol} exceeds available cash")
    return conn.execute(
        "INSERT INTO fills (order_id, qty, price, cost, source) VALUES (%s, %s, %s, %s, %s)"
        " RETURNING id",
        (order_id, qty, price, cost, source),
    ).fetchone()[0]


def equity(conn: psycopg.Connection, portfolio_id: int, prices: dict[str, Decimal]) -> Decimal:
    held = positions(conn, portfolio_id)
    missing = set(held) - set(prices)
    if missing:
        raise KeyError(f"no price for held symbols: {sorted(missing)}")
    return cash(conn, portfolio_id) + sum(q * prices[s] for s, q in held.items())
