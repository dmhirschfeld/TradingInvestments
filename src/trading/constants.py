"""Fixed value sets, kept in one place. Compare with `normalize` (case-insensitive)."""

BUY = "buy"
SELL = "sell"
SIDES = (BUY, SELL)

ORDER_PROPOSED = "proposed"
ORDER_VETOED = "vetoed"
ORDER_SUBMITTED = "submitted"
ORDER_FILLED = "filled"
ORDER_EXPIRED = "expired"

FILL_LEDGER = "ledger"
FILL_BROKER = "broker"

# FR15.3: every pipeline runs at both sizes.
ACCOUNT_SIZES = (5_000, 100_000)


def normalize(value: str) -> str:
    return value.strip().lower()
