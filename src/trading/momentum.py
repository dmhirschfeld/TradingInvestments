"""Momentum yardstick: 12-1 month cross-sectional momentum.

Return from about 12 months ago to 1 month ago (skipping the latest month,
which tends to reverse), ranked across the universe.
"""

from decimal import Decimal

LOOKBACK_DAYS = 252   # ~12 months of trading days
SKIP_DAYS = 21        # ~1 month


def score(closes: list[Decimal]) -> Decimal | None:
    """`closes` is oldest-first. None when history is too short to score."""
    if len(closes) < LOOKBACK_DAYS + 1:
        return None
    start = closes[-(LOOKBACK_DAYS + 1)]
    end = closes[-(SKIP_DAYS + 1)]
    if start <= 0:
        raise ValueError("non-positive start price")
    return end / start - 1


def top(history: dict[str, list[Decimal]], n: int) -> list[str]:
    scored = [(s, sym) for sym, closes in history.items() if (s := score(closes)) is not None]
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [sym for _, sym in scored[:n]]


def equal_weight_targets(picks: list[str], equity: Decimal,
                         prices: dict[str, Decimal]) -> dict[str, Decimal]:
    """Target quantity per pick; fractional shares allowed (FR6.4)."""
    if not picks:
        return {}
    each = equity / len(picks)
    return {sym: (each / prices[sym]).quantize(Decimal("0.000001")) for sym in picks}
