# Broker Adapter Contract

Only `src/trading/broker.py` talks to a broker (FR8.3).

| Method | Input | Output | Rules |
|---|---|---|---|
| `submit_limit_order` | client order id, symbol, side (`buy`/`sell`), qty (fractional allowed), limit price | broker order id | Day-only limit order (FR8.4). Same client order id twice must not create a second order. Alpaca rejects orders worth under $1, so callers never send one (`pipeline.MIN_ORDER_VALUE`). |
| `positions` | — | symbol → quantity | Non-zero positions only. |
| `order_fill` | client order id | status (lower-case), filled qty, average fill price or none | Read after the order's day has closed. |

Errors are raised, never swallowed; the evening run stops on any broker error.
Implementations: `AlpacaPaper` (keys from `<LABEL>_KEY_ID` / `<LABEL>_SECRET_KEY`), `FakeBroker` (tests).
