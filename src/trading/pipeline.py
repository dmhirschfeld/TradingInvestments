"""Phase 1 evening run. Each step records completion, so a rerun skips finished
steps and never doubles anything (NF2). Any failure stops the run loudly."""

from datetime import date, datetime
from decimal import Decimal

import psycopg

from trading import audit, data, ledger, momentum, reconcile, risk
from trading.broker import Broker
from trading.constants import (BUY, FILL_BROKER, FILL_LEDGER, ORDER_EXPIRED, ORDER_FILLED,
                               ORDER_PROPOSED, ORDER_SUBMITTED, ORDER_VETOED, SELL, normalize)
from trading.costs import CostModel
from trading.variants import BY_KEY

PHASE = 1
MOMENTUM_PICKS = 8
LIMIT_BAND = Decimal("0.005")       # FR8.4: limit = prior close +/- 0.5%
CASH_BUFFER = Decimal("0.99")       # keep 1% back for costs
MIN_ORDER_VALUE = Decimal("1")      # Alpaca rejects orders under $1; every portfolio follows the same rule
HOLD_SYMBOL = {"spy_hold": "SPY", "iwm_hold": "IWM"}


class DataQualityError(RuntimeError):
    pass


def _done(conn, day: date, step: str) -> bool:
    return conn.execute("SELECT 1 FROM run_steps WHERE run_day = %s AND step = %s",
                        (day, step)).fetchone() is not None


def _step(conn, day: date, step: str, fn) -> None:
    if _done(conn, day, step):
        return
    try:
        with conn.transaction():
            result = fn()
            conn.execute("INSERT INTO run_steps (run_day, step) VALUES (%s, %s)", (day, step))
    except Exception as exc:
        # Record the failure, then stop the run: the step is not marked done,
        # so the next run retries it.
        audit.append(conn, step, "step_failed", {"error": repr(exc)}, run_day=day)
        raise
    audit.append(conn, step, "step_done", {"result": result}, run_day=day)


def _active_portfolios(conn) -> list[tuple[int, str, str | None]]:
    rows = conn.execute("SELECT id, pipeline, mirror_account FROM portfolios ORDER BY id").fetchall()
    return [r for r in rows if BY_KEY[r[1]].active_from_phase <= PHASE]


def run_daily(conn: psycopg.Connection, day: date, known_at: datetime, source: data.BarSource,
              brokers: dict[str, Broker], costs: CostModel = CostModel(),
              limits: risk.RiskLimits = risk.RiskLimits()) -> None:
    _step(conn, day, "ingest", lambda: len(data.ingest(conn, source, day, known_at)))
    _step(conn, day, "quality", lambda: _quality(conn, day, known_at))
    _step(conn, day, "fills", lambda: _fills(conn, day, known_at, brokers, costs))
    _step(conn, day, "decide", lambda: _decide(conn, day, known_at, limits))
    _step(conn, day, "submit", lambda: _submit(conn, day, brokers))
    _step(conn, day, "reconcile", lambda: _reconcile(conn, brokers))


def _previous_day(conn, day: date) -> date | None:
    row = conn.execute("SELECT MAX(day) FROM daily_bars WHERE day < %s", (day,)).fetchone()
    return row[0]


def _quality(conn, day: date, known_at: datetime) -> int:
    today = data.bars_for_day(conn, day, known_at)
    prev_day = _previous_day(conn, day)
    prior = data.bars_for_day(conn, prev_day, known_at) if prev_day else {}
    held = set()
    for pid, _, _ in _active_portfolios(conn):
        held |= set(ledger.positions(conn, pid))
    problems = data.quality_problems(list(today.values()), set(prior) | held,
                                     {s: b.close for s, b in prior.items()})
    if problems:
        raise DataQualityError(f"{day}: {len(problems)} data problems, trading blocked: {problems[:5]}")
    return len(today)


def _fills(conn, day: date, known_at: datetime, brokers: dict[str, Broker], costs: CostModel) -> int:
    """Settle orders placed on earlier days: the broker reports mirrored ones,
    the ledger simulates the rest against today's bar."""
    bars = data.bars_for_day(conn, day, known_at)
    pending = conn.execute(
        "SELECT o.id, o.client_order_id, o.symbol, o.side, o.qty, o.limit_price, p.mirror_account"
        " FROM orders o JOIN portfolios p ON p.id = o.portfolio_id"
        " WHERE o.status = %s AND o.run_day < %s ORDER BY (o.side = %s) DESC, o.id",
        (ORDER_SUBMITTED, day, SELL),
    ).fetchall()
    filled = 0
    for oid, coid, sym, side, qty, limit, mirror in pending:
        side = normalize(side)
        if mirror:
            f = brokers[mirror].order_fill(coid)
            if f.filled_qty > 0:
                ledger.record_fill(conn, oid, f.filled_qty, f.filled_avg_price,
                                   costs.commission_per_order, FILL_BROKER)
                filled += 1
            status = ORDER_FILLED if f.status == ORDER_FILLED else ORDER_EXPIRED
        else:
            bar = bars.get(sym)
            if bar is None:
                raise DataQualityError(f"no bar for {sym} on {day} to settle order {coid}")
            reachable = bar.low <= limit if side == BUY else bar.high >= limit
            status = ORDER_EXPIRED
            if reachable:
                # Fill at the open or the limit, whichever the order would get;
                # spread and slippage are charged as an explicit cost.
                ref = min(bar.open, limit) if side == BUY else max(bar.open, limit)
                q = costs.fillable_qty(qty, Decimal(bar.volume))
                ledger.record_fill(conn, oid, q, ref, costs.cost(q, ref), FILL_LEDGER)
                filled += 1
                status = ORDER_FILLED
        conn.execute("UPDATE orders SET status = %s WHERE id = %s", (status, oid))
    return filled


def _targets(conn, pipeline: str, day: date, known_at: datetime, equity: Decimal,
             prices: dict[str, Decimal]) -> dict[str, Decimal] | None:
    """Target quantities, or None when this pipeline does not rebalance today."""
    if pipeline in HOLD_SYMBOL:
        sym = HOLD_SYMBOL[pipeline]
        return {sym: (equity * CASH_BUFFER / prices[sym]).quantize(Decimal("0.000001"))}
    if pipeline == "momentum":
        picks = momentum.top(data.closes_as_of(conn, known_at), MOMENTUM_PICKS)
        return momentum.equal_weight_targets(picks, equity * CASH_BUFFER, prices)
    raise ValueError(f"pipeline {pipeline} has no phase-{PHASE} targets")


def _rebalance_due(conn, portfolio_id: int, pipeline: str, day: date) -> bool:
    """Hold portfolios buy once; momentum rebalances on its first run each month."""
    if pipeline in HOLD_SYMBOL:
        return not conn.execute("SELECT 1 FROM orders WHERE portfolio_id = %s LIMIT 1",
                                (portfolio_id,)).fetchone()
    return not conn.execute(
        "SELECT 1 FROM orders WHERE portfolio_id = %s"
        " AND date_trunc('month', run_day) = date_trunc('month', %s::date) LIMIT 1",
        (portfolio_id, day)).fetchone()


def _decide(conn, day: date, known_at: datetime, limits: risk.RiskLimits) -> int:
    bars = data.bars_for_day(conn, day, known_at)
    prices = {s: b.close for s, b in bars.items()}
    prev_day = _previous_day(conn, day)
    prev_prices = {s: b.close for s, b in data.bars_for_day(conn, prev_day, known_at).items()} \
        if prev_day else prices
    created = 0
    for pid, pipeline, _ in _active_portfolios(conn):
        if not _rebalance_due(conn, pid, pipeline, day):
            continue
        name = conn.execute("SELECT name FROM portfolios WHERE id = %s", (pid,)).fetchone()[0]
        equity = ledger.equity(conn, pid, prices)
        held = ledger.positions(conn, pid)
        day_start = ledger.equity(conn, pid, {**prices, **prev_prices}) if held else equity
        targets = _targets(conn, pipeline, day, known_at, equity, prices)
        for sym in sorted(set(targets) | set(held)):
            delta = targets.get(sym, Decimal(0)) - held.get(sym, Decimal(0))
            if abs(delta) * prices[sym] < MIN_ORDER_VALUE:
                continue
            side = BUY if delta > 0 else SELL
            band = 1 + LIMIT_BAND if side == BUY else 1 - LIMIT_BAND
            p = risk.Proposal(sym, side, abs(delta), (prices[sym] * band).quantize(Decimal("0.01")))
            decision = risk.Decision(True)
            if BY_KEY[pipeline].risk_gate:
                decision = risk.check(
                    p, equity=equity, position_value=held.get(sym, Decimal(0)) * prices[sym],
                    avg_dollar_volume=data.avg_dollar_volume(conn, sym, known_at),
                    day_start_equity=day_start, limits=limits)
            status = ORDER_PROPOSED if decision.approved else ORDER_VETOED
            row = conn.execute(
                "INSERT INTO orders (portfolio_id, client_order_id, run_day, symbol, side, qty,"
                " limit_price, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (client_order_id) DO NOTHING RETURNING id",
                (pid, f"{name}-{day}-{sym}-{side}", day, sym, side, p.qty, p.limit_price, status),
            ).fetchone()
            if row and not decision.approved:
                audit.append(conn, "decide", "risk_veto",
                             {"portfolio": name, "symbol": sym, "rule": decision.rule}, run_day=day)
            created += row is not None
    return created


def _submit(conn, day: date, brokers: dict[str, Broker]) -> int:
    rows = conn.execute(
        "SELECT o.id, o.client_order_id, o.symbol, o.side, o.qty, o.limit_price, p.mirror_account"
        " FROM orders o JOIN portfolios p ON p.id = o.portfolio_id"
        " WHERE o.run_day = %s AND o.status = %s ORDER BY o.id",
        (day, ORDER_PROPOSED),
    ).fetchall()
    for oid, coid, sym, side, qty, limit, mirror in rows:
        if mirror:
            if mirror not in brokers:
                raise RuntimeError(f"no broker configured for mirrored account {mirror}")
            brokers[mirror].submit_limit_order(coid, sym, side, qty, limit)
        conn.execute("UPDATE orders SET status = %s WHERE id = %s", (ORDER_SUBMITTED, oid))
    return len(rows)


def _reconcile(conn, brokers: dict[str, Broker]) -> int:
    checked = 0
    for pid, _, mirror in _active_portfolios(conn):
        if mirror:
            reconcile.check(conn, pid, brokers[mirror])
            checked += 1
    return checked
