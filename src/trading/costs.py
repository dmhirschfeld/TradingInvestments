"""One shared cost model for every portfolio (FR9.2), so comparisons are like for like."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CostModel:
    half_spread_bps: Decimal = Decimal("5")    # half the bid-ask gap, paid on every trade
    slippage_bps: Decimal = Decimal("5")       # price moving against us while filling
    commission_per_order: Decimal = Decimal("0")
    max_adv_fraction: Decimal = Decimal("0.05")  # never fill more than 5% of average daily volume

    def cost(self, qty: Decimal, reference_price: Decimal) -> Decimal:
        """Money lost to spread, slippage and commission versus the reference price."""
        bps = (self.half_spread_bps + self.slippage_bps) / Decimal(10_000)
        return reference_price * bps * qty + self.commission_per_order

    def fillable_qty(self, qty: Decimal, avg_daily_volume: Decimal) -> Decimal:
        return min(qty, avg_daily_volume * self.max_adv_fraction)
