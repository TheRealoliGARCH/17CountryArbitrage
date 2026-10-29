"""Reference rules for the 17-State Market.

This module is a deliberately small specification layer, not a broker,
exchange gateway, or production trading engine. It models permitted local
transitions and a few critical decision guards.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import FrozenSet, Mapping


class State(str, Enum):
    OPEN = "O"
    HIGH = "H"
    LOW = "L"
    CLOSE = "C"
    INTROSPECTION = "I"
    REFLECTION = "R"
    ARBITRAGE = "A"
    SETTLEMENT = "S"
    DELISTING = "D"
    RETROSPECTION = "T"
    DATA_VALIDATION = "V"
    RISK_ASSESSMENT = "K"
    ORDER_EXECUTION = "E"
    CLEARING = "Q"
    SUSPENSION = "U"
    RELISTING = "J"
    MODEL_REVISION = "M"


class Subsystem(str, Enum):
    PRICE_FORMATION = "price_formation"
    MARKET_INTELLIGENCE = "market_intelligence"
    TRANSACTION_OPERATIONS = "transaction_operations"
    INSTITUTIONAL_GOVERNANCE = "institutional_governance"
    LEARNING_EVALUATION = "learning_evaluation"


SUBSYSTEM_STATES: Mapping[Subsystem, FrozenSet[State]] = {
    Subsystem.PRICE_FORMATION: frozenset(
        {State.OPEN, State.HIGH, State.LOW, State.CLOSE}
    ),
    Subsystem.MARKET_INTELLIGENCE: frozenset(
        {State.DATA_VALIDATION, State.INTROSPECTION,
         State.REFLECTION, State.ARBITRAGE}
    ),
    Subsystem.TRANSACTION_OPERATIONS: frozenset(
        {State.ORDER_EXECUTION, State.CLEARING, State.SETTLEMENT}
    ),
    Subsystem.INSTITUTIONAL_GOVERNANCE: frozenset(
        {State.RISK_ASSESSMENT, State.DELISTING,
         State.SUSPENSION, State.RELISTING}
    ),
    Subsystem.LEARNING_EVALUATION: frozenset(
        {State.RETROSPECTION, State.MODEL_REVISION}
    ),
}

# Structural adjacency. Guards below decide whether a permitted transition
# is enabled in a given context. Self-loops represent continued processing.
TRANSITIONS: Mapping[State, FrozenSet[State]] = {
    State.OPEN: frozenset({State.HIGH, State.LOW, State.CLOSE}),
    State.HIGH: frozenset({State.LOW, State.CLOSE}),
    State.LOW: frozenset({State.HIGH, State.CLOSE}),
    State.CLOSE: frozenset({State.OPEN, State.DATA_VALIDATION, State.RETROSPECTION}),
    State.DATA_VALIDATION: frozenset({State.DATA_VALIDATION, State.INTROSPECTION}),
    State.INTROSPECTION: frozenset({
        State.INTROSPECTION, State.REFLECTION, State.ARBITRAGE,
        State.RISK_ASSESSMENT, State.RETROSPECTION,
    }),
    State.REFLECTION: frozenset({
        State.INTROSPECTION, State.ARBITRAGE,
        State.RISK_ASSESSMENT, State.RETROSPECTION,
    }),
    State.ARBITRAGE: frozenset({
        State.INTROSPECTION, State.ORDER_EXECUTION,
        State.RISK_ASSESSMENT, State.RETROSPECTION,
    }),
    State.ORDER_EXECUTION: frozenset({
        State.ORDER_EXECUTION, State.CLEARING, State.RISK_ASSESSMENT,
    }),
    State.CLEARING: frozenset({
        State.CLEARING, State.SETTLEMENT, State.RISK_ASSESSMENT,
    }),
    State.SETTLEMENT: frozenset({
        State.SETTLEMENT, State.RETROSPECTION, State.RISK_ASSESSMENT,
    }),
    State.RISK_ASSESSMENT: frozenset({
        State.RISK_ASSESSMENT, State.INTROSPECTION,
        State.SUSPENSION, State.DELISTING, State.RETROSPECTION,
    }),
    State.SUSPENSION: frozenset({
        State.SUSPENSION, State.RISK_ASSESSMENT, State.INTROSPECTION,
    }),
    State.DELISTING: frozenset({
        State.DELISTING, State.RELISTING, State.RETROSPECTION,
    }),
    State.RELISTING: frozenset({
        State.RELISTING, State.DELISTING, State.DATA_VALIDATION,
    }),
    State.RETROSPECTION: frozenset({
        State.RETROSPECTION, State.INTROSPECTION, State.MODEL_REVISION,
    }),
    State.MODEL_REVISION: frozenset({
        State.MODEL_REVISION, State.DATA_VALIDATION, State.RETROSPECTION,
    }),
}


@dataclass(frozen=True)
class OHLC:
    open: float
    high: float
    low: float
    close: float

    def is_valid(self) -> bool:
        """Return whether all four prices are finite and OHLC-consistent."""
        values = (self.open, self.high, self.low, self.close)
        return (
            all(isfinite(value) for value in values)
            and self.low <= min(self.open, self.close)
            and self.high >= max(self.open, self.close)
            and self.low <= self.high
        )


@dataclass(frozen=True)
class ArbitrageContext:
    data_valid: bool
    net_profit: float
    minimum_profit: float = 0.0
    sufficient_liquidity: bool = False
    risk_policy_passed: bool = False

    def may_execute(self) -> bool:
        """Check the proposed execution guard; this does not place an order."""
        return (
            self.data_valid
            and isfinite(self.net_profit)
            and isfinite(self.minimum_profit)
            and self.net_profit > self.minimum_profit
            and self.sufficient_liquidity
            and self.risk_policy_passed
        )


@dataclass(frozen=True)
class DelistingContext:
    negative_premium_signal: bool
    risk_assessment_complete: bool
    delisting_criteria_satisfied: bool
    authorization_obtained: bool

    def may_delist(self) -> bool:
        """Negative premium alone is never sufficient for delisting."""
        return (
            self.negative_premium_signal
            and self.risk_assessment_complete
            and self.delisting_criteria_satisfied
            and self.authorization_obtained
        )


def transition_permitted(source: State, destination: State) -> bool:
    """Test structural adjacency only, not context-dependent guard validity."""
    return destination in TRANSITIONS[source]


def may_settle(clearing_complete: bool) -> bool:
    """A transaction on the normal route can settle only after clearing."""
    return clearing_complete


def may_submit_ordinary_order(is_suspended: bool, ordinary_guard_passed: bool) -> bool:
    """Block new ordinary orders for a suspended instrument."""
    return not is_suspended and ordinary_guard_passed


def may_activate_model_revision(
    tests_passed: bool, approval_obtained: bool
) -> bool:
    """A candidate model activates only after tests and approval."""
    return tests_passed and approval_obtained
