"""Basic risk gate for phase 1: a hard veto on every proposed order (FR7).

Phase 2 adds regime exposure limits and the market-shock buying freeze.
"""

from dataclasses import dataclass
from decimal import Decimal

from trading.constants import BUY, normalize


@dataclass(frozen=True)
class RiskLimits:
    max_name_weight: Decimal = Decimal("0.15")
    max_adv_fraction: Decimal = Decimal("0.05")    # order <= 5% of 20-day average dollar volume
    daily_loss_stop: Decimal = Decimal("0.03")     # no new buys after a 3% loss today


@dataclass(frozen=True)
class Proposal:
    symbol: str
    side: str
    qty: Decimal
    limit_price: Decimal


@dataclass(frozen=True)
class Decision:
    approved: bool
    rule: str | None = None     # the rule that fired, logged with every veto (RM1)


def check(p: Proposal, *, equity: Decimal, position_value: Decimal,
          avg_dollar_volume: Decimal, day_start_equity: Decimal,
          limits: RiskLimits = RiskLimits()) -> Decision:
    if normalize(p.side) != BUY:
        return Decision(True)   # selling only reduces risk
    notional = p.qty * p.limit_price
    if equity <= 0:
        return Decision(False, "no_equity")
    if day_start_equity > 0 and (day_start_equity - equity) / day_start_equity >= limits.daily_loss_stop:
        return Decision(False, "daily_loss_stop")
    if (position_value + notional) / equity > limits.max_name_weight:
        return Decision(False, "max_name_weight")
    if notional > avg_dollar_volume * limits.max_adv_fraction:
        return Decision(False, "liquidity")
    return Decision(True)
