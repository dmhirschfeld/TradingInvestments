"""End-to-end phase 1 evening run against synthetic recorded data."""

import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest

from trading import audit, ledger, pipeline, variants
from trading.broker import FakeBroker
from trading.data import FixtureSource

START = date(2025, 9, 1)
HISTORY = 260
STOCKS = {f"S{i:02d}": 1 + i / 1000 for i in range(10)}   # daily growth factor; S09 strongest
ETFS = {"SPY": 1.0004, "IWM": 1.0002}


def _known(d: date) -> datetime:
    return datetime.combine(d, time(22), tzinfo=timezone.utc)


def _bars(n: int) -> list[dict]:
    out = []
    for sym, g in {**STOCKS, **ETFS}.items():
        px = round(50 * g ** n, 4)
        out.append(dict(symbol=sym, open=px, high=px * 1.01, low=px * 0.99, close=px,
                        volume=1_000_000))
    return out


@pytest.fixture
def world(conn, tmp_path):
    for n in range(HISTORY):
        d = START + timedelta(days=n)
        for b in _bars(n):
            conn.execute(
                "INSERT INTO daily_bars (symbol, day, open, high, low, close, volume, known_at, source)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'history')",
                (b["symbol"], d, b["open"], b["high"], b["low"], b["close"], b["volume"], _known(d)))
    days = {(START + timedelta(days=n)).isoformat(): _bars(n) for n in range(HISTORY, HISTORY + 3)}
    path = tmp_path / "bars.json"
    path.write_text(json.dumps(days))
    variants.seed(conn)
    return FixtureSource(path), START + timedelta(days=HISTORY)


def _pid(conn, name):
    return conn.execute("SELECT id FROM portfolios WHERE name = %s", (name,)).fetchone()[0]


def test_first_run_places_orders_and_mirrors_momentum(conn, world):
    source, day1 = world
    broker = FakeBroker()
    pipeline.run_daily(conn, day1, _known(day1), source, {"alpaca_paper_1": broker})

    picks = conn.execute(
        "SELECT DISTINCT symbol FROM orders o JOIN portfolios p ON p.id = o.portfolio_id"
        " WHERE p.name = 'momentum_5000' ORDER BY symbol").fetchall()
    assert [p[0] for p in picks] == [f"S{i:02d}" for i in range(2, 10)]   # top 8 by momentum
    assert len(broker.orders) == 8                                      # only the $5,000 mirror
    spy = conn.execute("SELECT symbol, status FROM orders o JOIN portfolios p ON p.id = o.portfolio_id"
                       " WHERE p.name = 'spy_hold_100000'").fetchall()
    assert spy == [("SPY", "submitted")]
    assert conn.execute("SELECT count(*) FROM orders o JOIN portfolios p ON p.id = o.portfolio_id"
                        " WHERE p.pipeline LIKE 'claude%'").fetchone()[0] == 0
    audit.verify(conn)

    # Rerunning the same evening changes nothing (NF2).
    before = conn.execute("SELECT count(*) FROM orders").fetchone()[0]
    pipeline.run_daily(conn, day1, _known(day1), source, {"alpaca_paper_1": broker})
    assert conn.execute("SELECT count(*) FROM orders").fetchone()[0] == before


def test_next_run_settles_fills_and_reconciles(conn, world):
    source, day1 = world
    broker = FakeBroker()
    pipeline.run_daily(conn, day1, _known(day1), source, {"alpaca_paper_1": broker})
    for coid, o in broker.orders.items():
        broker.simulate_fill(coid, o["limit_price"])

    day2 = day1 + timedelta(days=1)
    pipeline.run_daily(conn, day2, _known(day2), source, {"alpaca_paper_1": broker})

    mirrored = _pid(conn, "momentum_5000")
    assert ledger.positions(conn, mirrored) == broker.positions()
    simulated = _pid(conn, "momentum_100000")
    held = ledger.positions(conn, simulated)
    assert len(held) == 8 and all(q > 0 for q in held.values())
    assert 0 < ledger.cash(conn, simulated) < Decimal("100000") * Decimal("0.02")
    assert conn.execute("SELECT count(*) FROM fills WHERE source = 'broker'").fetchone()[0] == 8


def test_broker_mismatch_halts_and_is_logged(conn, world):
    source, day1 = world
    broker = FakeBroker()
    pipeline.run_daily(conn, day1, _known(day1), source, {"alpaca_paper_1": broker})
    for coid, o in broker.orders.items():
        broker.simulate_fill(coid, o["limit_price"])
    broker.held["S09"] -= Decimal("1")      # the broker disagrees with what it reported

    day2 = day1 + timedelta(days=1)
    with pytest.raises(Exception, match="ledger vs broker"):
        pipeline.run_daily(conn, day2, _known(day2), source, {"alpaca_paper_1": broker})
    assert conn.execute("SELECT 1 FROM run_steps WHERE run_day = %s AND step = 'reconcile'",
                        (day2,)).fetchone() is None
    assert conn.execute("SELECT kind FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()[0] \
        == "step_failed"


def test_bad_data_blocks_trading(conn, world, tmp_path):
    source, day1 = world
    bad = {day1.isoformat(): [b for b in _bars(HISTORY) if b["symbol"] != "SPY"]}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad))
    with pytest.raises(pipeline.DataQualityError, match="SPY: missing bar"):
        pipeline.run_daily(conn, day1, _known(day1), FixtureSource(path),
                           {"alpaca_paper_1": FakeBroker()})
    assert conn.execute("SELECT count(*) FROM orders").fetchone()[0] == 0


def test_orders_under_one_dollar_are_skipped(conn, world):
    """Alpaca rejects orders under $1, so no portfolio places one (MIN_ORDER_VALUE)."""
    source, day1 = world
    pid = _pid(conn, "momentum_100000")
    price = Decimal(str(round(50 * STOCKS["S09"] ** HISTORY, 4)))
    target = (Decimal("100000") * pipeline.CASH_BUFFER / pipeline.MOMENTUM_PICKS / price) \
        .quantize(Decimal("0.000001"))
    oid = conn.execute(
        "INSERT INTO orders (portfolio_id, client_order_id, run_day, symbol, side, qty, limit_price,"
        " status) VALUES (%s, 'earlier-S09', %s, 'S09', 'buy', %s, %s, 'filled') RETURNING id",
        (pid, day1 - timedelta(days=40), target - Decimal("0.001"), price)).fetchone()[0]
    ledger.record_fill(conn, oid, target - Decimal("0.001"), price, Decimal(0), "ledger")

    pipeline.run_daily(conn, day1, _known(day1), source, {"alpaca_paper_1": FakeBroker()})

    today = {r[0] for r in conn.execute(
        "SELECT symbol FROM orders WHERE portfolio_id = %s AND run_day = %s", (pid, day1))}
    assert "S09" not in today                      # 0.001 share short of target is worth < $1
    assert today == {f"S{i:02d}" for i in range(2, 9)}
