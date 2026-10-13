from datetime import date, datetime, timezone
from decimal import Decimal

import psycopg
import pytest

from trading import audit, data, ledger, momentum, reconcile, risk, variants
from trading.broker import FakeBroker
from trading.constants import BUY, SELL


def _portfolio(conn, name="p", cash=Decimal("5000"), mirror=None):
    return conn.execute(
        "INSERT INTO portfolios (name, pipeline, starting_cash, mirror_account)"
        " VALUES (%s, 'momentum', %s, %s) RETURNING id", (name, cash, mirror)).fetchone()[0]


def _order(conn, pid, sym, side, qty, price, coid):
    return conn.execute(
        "INSERT INTO orders (portfolio_id, client_order_id, run_day, symbol, side, qty, limit_price,"
        " status) VALUES (%s, %s, '2026-10-12', %s, %s, %s, %s, 'submitted') RETURNING id",
        (pid, coid, sym, side, qty, price)).fetchone()[0]


# --- audit log -------------------------------------------------------------

def test_audit_chain_verifies_and_blocks_edits(conn):
    audit.append(conn, "ingest", "step_done", {"n": 3})
    audit.append(conn, "decide", "risk_veto", {"rule": "liquidity"})
    audit.verify(conn)
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        conn.execute("UPDATE audit_log SET payload = '{}'")
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        conn.execute("DELETE FROM audit_log")


# --- ledger ----------------------------------------------------------------

def test_ledger_cash_and_positions_follow_fills(conn):
    pid = _portfolio(conn)
    buy = _order(conn, pid, "AAA", BUY, Decimal("10"), Decimal("100"), "b1")
    ledger.record_fill(conn, buy, Decimal("10"), Decimal("100"), Decimal("1"), "ledger")
    assert ledger.positions(conn, pid) == {"AAA": Decimal("10")}
    assert ledger.cash(conn, pid) == Decimal("3999")          # 5000 - 1000 - 1 cost
    sell = _order(conn, pid, "AAA", SELL, Decimal("4"), Decimal("110"), "s1")
    ledger.record_fill(conn, sell, Decimal("4"), Decimal("110"), Decimal("1"), "ledger")
    assert ledger.positions(conn, pid) == {"AAA": Decimal("6")}
    assert ledger.cash(conn, pid) == Decimal("4438")          # + 440 - 1 cost
    assert ledger.equity(conn, pid, {"AAA": Decimal("120")}) == Decimal("5158")


def test_ledger_rejects_overselling_and_overspending(conn):
    pid = _portfolio(conn)
    sell = _order(conn, pid, "AAA", SELL, Decimal("1"), Decimal("10"), "s1")
    with pytest.raises(ValueError, match="exceeds the position"):
        ledger.record_fill(conn, sell, Decimal("1"), Decimal("10"), Decimal("0"), "ledger")
    buy = _order(conn, pid, "AAA", BUY, Decimal("100"), Decimal("100"), "b1")
    with pytest.raises(ValueError, match="exceeds available cash"):
        ledger.record_fill(conn, buy, Decimal("100"), Decimal("100"), Decimal("0"), "ledger")
    assert ledger.positions(conn, pid) == {}


# --- risk gate -------------------------------------------------------------

def _check(**kw):
    base = dict(equity=Decimal("5000"), position_value=Decimal("0"),
                avg_dollar_volume=Decimal("10000000"), day_start_equity=Decimal("5000"))
    base.update(kw)
    return risk.check(risk.Proposal("AAA", BUY, Decimal("5"), Decimal("100")), **base)


def test_risk_gate_vetoes_each_rule():
    assert _check() == risk.Decision(True)
    assert _check(position_value=Decimal("300")).rule == "max_name_weight"   # 800/5000 > 15%
    assert _check(avg_dollar_volume=Decimal("9000")).rule == "liquidity"     # 500 > 5% of 9000
    assert _check(equity=Decimal("4800")).rule == "daily_loss_stop"          # down 4% today
    sell = risk.Proposal("AAA", "SELL", Decimal("5"), Decimal("100"))
    assert risk.check(sell, equity=Decimal("1"), position_value=Decimal("0"),
                      avg_dollar_volume=Decimal("0"), day_start_equity=Decimal("5000")).approved


# --- momentum --------------------------------------------------------------

def test_momentum_skips_last_month_and_short_history():
    rising = [Decimal(100 + i) for i in range(253)]
    falling = [Decimal(400 - i) for i in range(253)]
    assert momentum.score(rising[:200]) is None
    s = momentum.score(rising)
    assert s == Decimal(100 + 252 - 21) / Decimal(100) - 1
    assert momentum.top({"UP": rising, "DOWN": falling, "NEW": rising[:10]}, 1) == ["UP"]


# --- data quality ----------------------------------------------------------

def _bar(sym, close, volume=1000, day=date(2026, 10, 12)):
    c = Decimal(str(close))
    return data.Bar(sym, day, c, c, c, c, volume)


def test_quality_flags_missing_split_and_bad_prices():
    problems = data.quality_problems(
        [_bar("AAA", 50), _bar("BBB", -1), _bar("CCC", 10, volume=0)],
        expected={"AAA", "BBB", "CCC", "DDD"},
        prior_close={"AAA": Decimal("100"), "CCC": Decimal("10")})
    assert "DDD: missing bar" in problems
    assert "BBB: non-positive price" in problems
    assert "CCC: stale price" in problems
    assert any(p.startswith("AAA") and "split" in p for p in problems)
    assert data.quality_problems([_bar("AAA", 101)], {"AAA"}, {"AAA": Decimal("100")}) == []


def test_point_in_time_reads_ignore_later_corrections(conn):
    t1 = datetime(2026, 10, 12, 22, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 13, 22, tzinfo=timezone.utc)
    for close, known in ((100, t1), (105, t2)):
        conn.execute(
            "INSERT INTO daily_bars (symbol, day, open, high, low, close, volume, known_at, source)"
            " VALUES ('AAA', '2026-10-12', %s, %s, %s, %s, 1, %s, 'test')",
            (close, close, close, close, known))
    assert data.closes_as_of(conn, t1) == {"AAA": [Decimal("100")]}
    assert data.closes_as_of(conn, t2) == {"AAA": [Decimal("105")]}


# --- reconciliation and variants -------------------------------------------

def test_reconcile_halts_on_mismatch(conn):
    pid = _portfolio(conn, mirror="alpaca_paper_1")
    buy = _order(conn, pid, "AAA", BUY, Decimal("2.5"), Decimal("100"), "b1")
    ledger.record_fill(conn, buy, Decimal("2.5"), Decimal("100"), Decimal("0"), "broker")
    reconcile.check(conn, pid, FakeBroker(held={"AAA": Decimal("2.5")}))
    with pytest.raises(reconcile.ReconciliationError):
        reconcile.check(conn, pid, FakeBroker(held={"AAA": Decimal("2")}))


def test_seed_creates_every_pipeline_at_both_sizes_once(conn):
    assert variants.seed(conn) == len(variants.PIPELINES) * 2
    assert variants.seed(conn) == 0
    mirrors = conn.execute(
        "SELECT name FROM portfolios WHERE mirror_account IS NOT NULL ORDER BY name").fetchall()
    assert [m[0] for m in mirrors] == ["claude_formula_5000", "claude_sizes_5000", "momentum_5000"]
