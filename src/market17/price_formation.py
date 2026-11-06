"""Deterministic price-formation primitives for the 17-State Market.

Research reference implementation only. This module does not connect to an
exchange or transmit orders.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Dict, Iterable, Optional, Tuple


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Order:
    order_id: str
    instrument_id: str
    participant_id: str
    side: Side
    price: float
    quantity: float
    timestamp: int
    sequence: int = 0

    def validate(self) -> None:
        if not all((self.order_id, self.instrument_id, self.participant_id)):
            raise ValueError("order, instrument, and participant IDs are required")
        if not isfinite(self.price) or self.price <= 0:
            raise ValueError("price must be finite and positive")
        if not isfinite(self.quantity) or self.quantity <= 0:
            raise ValueError("quantity must be finite and positive")


@dataclass
class OrderBook:
    instrument_id: str
    orders: Dict[str, Order] = field(default_factory=dict)

    def add(self, order: Order) -> None:
        order.validate()
        if order.instrument_id != self.instrument_id:
            raise ValueError("order instrument does not match this book")
        if order.order_id in self.orders:
            raise ValueError("duplicate order_id")
        self.orders[order.order_id] = order

    def cancel(self, order_id: str) -> Order:
        try:
            return self.orders.pop(order_id)
        except KeyError as exc:
            raise KeyError("unknown order_id") from exc

    def levels(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        buys = [o for o in self.orders.values() if o.side is Side.BUY]
        sells = [o for o in self.orders.values() if o.side is Side.SELL]
        bid = max((o.price for o in buys), default=None)
        ask = min((o.price for o in sells), default=None)
        bid_qty = sum(o.quantity for o in buys if o.price == bid) if bid is not None else 0.0
        ask_qty = sum(o.quantity for o in sells if o.price == ask) if ask is not None else 0.0
        return (bid, bid_qty), (ask, ask_qty)

    def best_bid_ask(self) -> Tuple[Optional[float], Optional[float]]:
        (bid, _), (ask, _) = self.levels()
        return bid, ask


@dataclass(frozen=True)
class AuctionResult:
    price: Optional[float]
    quantity: float
    eligible_buy_quantity: float
    eligible_sell_quantity: float


def call_auction(orders: Iterable[Order], reference_price: Optional[float] = None) -> AuctionResult:
    """Choose the price maximizing executable volume, then minimizing imbalance.

    Remaining ties use the reference price (when supplied), then the lower
    price. This deterministic rule is a research convention, not an exchange
    rulebook.
    """
    rows = list(orders)
    for row in rows:
        row.validate()
    if not rows:
        return AuctionResult(None, 0.0, 0.0, 0.0)
    candidates = sorted({row.price for row in rows})
    scored = []
    for price in candidates:
        demand = sum(row.quantity for row in rows if row.side is Side.BUY and row.price >= price)
        supply = sum(row.quantity for row in rows if row.side is Side.SELL and row.price <= price)
        scored.append((price, min(demand, supply), abs(demand - supply), demand, supply))
    max_volume = max(item[1] for item in scored)
    finalists = [item for item in scored if item[1] == max_volume]
    min_imbalance = min(item[2] for item in finalists)
    finalists = [item for item in finalists if item[2] == min_imbalance]
    if reference_price is not None:
        if not isfinite(reference_price) or reference_price <= 0:
            raise ValueError("reference_price must be finite and positive")
        finalists.sort(key=lambda item: (abs(item[0] - reference_price), item[0]))
    else:
        finalists.sort(key=lambda item: item[0])
    price, volume, _, demand, supply = finalists[0]
    return AuctionResult(price, volume, demand, supply)


@dataclass
class CircuitBreaker:
    """Simple reference-price move guard; explicit reset is required."""
    threshold_fraction: float
    halted: bool = False
    reason: str = ""

    def __post_init__(self) -> None:
        if not isfinite(self.threshold_fraction) or not 0 < self.threshold_fraction < 1:
            raise ValueError("threshold_fraction must be between zero and one")

    def observe(self, reference_price: float, observed_price: float) -> bool:
        if not isfinite(reference_price) or reference_price <= 0:
            raise ValueError("reference_price must be finite and positive")
        if not isfinite(observed_price) or observed_price <= 0:
            raise ValueError("observed_price must be finite and positive")
        move = abs(observed_price / reference_price - 1.0)
        if move >= self.threshold_fraction:
            self.halted = True
            self.reason = "price-move threshold reached"
        return self.halted

    def reset(self, *, authorized: bool) -> None:
        if not authorized:
            raise PermissionError("authorized reset is required")
        self.halted = False
        self.reason = ""
