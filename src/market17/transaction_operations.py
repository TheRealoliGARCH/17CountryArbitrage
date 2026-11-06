"""Clearing, settlement, collateral, and margin reference controls."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Dict


class TransactionStage(str, Enum):
    ACCEPTED = "accepted"
    EXECUTED = "executed"
    CLEARED = "cleared"
    SETTLED = "settled"
    FAILED = "failed"


@dataclass(frozen=True)
class CollateralPosition:
    participant_id: str
    currency: str
    market_value: float
    haircut: float

    def eligible_value(self) -> float:
        if not self.participant_id or not self.currency:
            raise ValueError("participant_id and currency are required")
        if not isfinite(self.market_value) or self.market_value < 0:
            raise ValueError("market_value must be finite and nonnegative")
        if not isfinite(self.haircut) or not 0 <= self.haircut < 1:
            raise ValueError("haircut must be in [0, 1)")
        return self.market_value * (1.0 - self.haircut)


@dataclass(frozen=True)
class MarginRequirement:
    initial_margin: float
    variation_margin: float
    currency: str

    @property
    def total(self) -> float:
        if not self.currency:
            raise ValueError("currency is required")
        if any(not isfinite(x) or x < 0 for x in
               (self.initial_margin, self.variation_margin)):
            raise ValueError("margin amounts must be finite and nonnegative")
        return self.initial_margin + self.variation_margin


@dataclass(frozen=True)
class ClearingResult:
    transaction_id: str
    accepted: bool
    required_amount: float
    eligible_collateral: float
    shortfall: float


def assess_collateral(
    transaction_id: str,
    required_amount: float,
    positions: Dict[str, CollateralPosition],
) -> ClearingResult:
    if not transaction_id:
        raise ValueError("transaction_id is required")
    if not isfinite(required_amount) or required_amount < 0:
        raise ValueError("required_amount must be finite and nonnegative")
    eligible = sum(position.eligible_value() for position in positions.values())
    shortfall = max(0.0, required_amount - eligible)
    return ClearingResult(transaction_id, shortfall == 0.0,
                          required_amount, eligible, shortfall)


def may_settle_after_clearing(clearing_accepted: bool, settlement_instruction_valid: bool) -> bool:
    """Settlement requires an accepted clearing result and valid instruction."""
    return bool(clearing_accepted and settlement_instruction_valid)
