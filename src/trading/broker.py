"""Broker adapter (FR8.3). Only this module talks to a broker.

Alpaca paper first; Interactive Brokers later behind the same interface.
"""

import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

import httpx

from trading.constants import BUY, SIDES, normalize

ALPACA_PAPER_URL = "https://paper-api.alpaca.markets"


class Broker(Protocol):
    def submit_limit_order(self, client_order_id: str, symbol: str, side: str,
                           qty: Decimal, limit_price: Decimal) -> str: ...

    def positions(self) -> dict[str, Decimal]: ...

    def order_fill(self, client_order_id: str) -> "BrokerFill": ...


@dataclass(frozen=True)
class BrokerFill:
    status: str                     # the broker's order status, lower-case
    filled_qty: Decimal
    filled_avg_price: Decimal | None


class AlpacaPaper:
    """One Alpaca paper account. Keys come from env vars named after the account label,
    e.g. label `alpaca_paper_1` reads ALPACA_PAPER_1_KEY_ID / ALPACA_PAPER_1_SECRET_KEY."""

    def __init__(self, account_label: str, client: httpx.Client | None = None):
        prefix = account_label.upper()
        key_id = os.environ.get(f"{prefix}_KEY_ID")
        secret = os.environ.get(f"{prefix}_SECRET_KEY")
        if not key_id or not secret:
            raise RuntimeError(f"{prefix}_KEY_ID / {prefix}_SECRET_KEY are not set")
        self._http = client or httpx.Client(base_url=ALPACA_PAPER_URL, timeout=30)
        self._headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret}

    def submit_limit_order(self, client_order_id: str, symbol: str, side: str,
                           qty: Decimal, limit_price: Decimal) -> str:
        side = normalize(side)
        if side not in SIDES:
            raise ValueError(f"unknown side {side!r}")
        # FR8.4: day-only limit orders for the next open. Fractional qty with limit
        # orders is not yet confirmed against Alpaca; a rejection surfaces as an HTTP error.
        r = self._http.post("/v2/orders", headers=self._headers, json={
            "symbol": symbol, "side": side, "type": "limit", "time_in_force": "day",
            "qty": str(qty), "limit_price": str(limit_price),
            "client_order_id": client_order_id,
        })
        r.raise_for_status()
        return r.json()["id"]

    def positions(self) -> dict[str, Decimal]:
        r = self._http.get("/v2/positions", headers=self._headers)
        r.raise_for_status()
        return {p["symbol"]: Decimal(p["qty"]) for p in r.json()}

    def order_fill(self, client_order_id: str) -> BrokerFill:
        r = self._http.get("/v2/orders:by_client_order_id", headers=self._headers,
                           params={"client_order_id": client_order_id})
        r.raise_for_status()
        o = r.json()
        price = o.get("filled_avg_price")
        return BrokerFill(normalize(o["status"]), Decimal(o["filled_qty"]),
                          Decimal(price) if price is not None else None)


@dataclass
class FakeBroker:
    """In-memory broker for tests; fills nothing on its own."""
    held: dict[str, Decimal] = field(default_factory=dict)
    orders: dict[str, dict] = field(default_factory=dict)

    def submit_limit_order(self, client_order_id: str, symbol: str, side: str,
                           qty: Decimal, limit_price: Decimal) -> str:
        if client_order_id in self.orders:     # idempotent like a real broker (FR8.1)
            return client_order_id
        self.orders[client_order_id] = dict(symbol=symbol, side=normalize(side),
                                            qty=qty, limit_price=limit_price)
        return client_order_id

    fills: dict[str, BrokerFill] = field(default_factory=dict)

    def positions(self) -> dict[str, Decimal]:
        return {s: q for s, q in self.held.items() if q != 0}

    def order_fill(self, client_order_id: str) -> BrokerFill:
        if client_order_id not in self.orders:
            raise LookupError(f"unknown order {client_order_id}")
        return self.fills.get(client_order_id, BrokerFill("new", Decimal(0), None))

    def simulate_fill(self, client_order_id: str, price: Decimal) -> None:
        """Test helper: fill an order completely at `price`."""
        o = self.orders[client_order_id]
        sign = 1 if o["side"] == BUY else -1
        self.held[o["symbol"]] = self.held.get(o["symbol"], Decimal(0)) + sign * o["qty"]
        self.fills[client_order_id] = BrokerFill("filled", o["qty"], price)
