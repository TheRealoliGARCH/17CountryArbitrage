"""Bounded state-space exploration for a compact 17-State Market abstraction.

This is a finite research model for checking selected safety invariants. It is
not a proof of the full market model and does not replace event_processor.py.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, Iterable, List, Optional, Tuple


class ListingStatus(str, Enum):
    LISTED = "listed"
    SUSPENDED = "suspended"
    DELISTED = "delisted"


class ModelStatus(str, Enum):
    ACTIVE = "active"
    REVISING = "revising"
    TESTED = "tested"
    APPROVED = "approved"


class Action(str, Enum):
    SUSPEND = "suspend"
    RESUME = "resume"
    DELIST = "delist"
    MARK_RELIST_ELIGIBLE = "mark_relist_eligible"
    APPROVE_RELISTING = "approve_relisting"
    RELIST = "relist"
    SUBMIT_ORDER = "submit_order"
    EXECUTE = "execute"
    CLEAR = "clear"
    SETTLE = "settle"
    BEGIN_MODEL_REVISION = "begin_model_revision"
    TEST_MODEL_REVISION = "test_model_revision"
    APPROVE_MODEL_REVISION = "approve_model_revision"
    ACTIVATE_MODEL_REVISION = "activate_model_revision"


@dataclass(frozen=True)
class MarketState:
    listing: ListingStatus = ListingStatus.LISTED
    transaction_stage: int = 0
    relist_eligible: bool = False
    relist_approved: bool = False
    model_status: ModelStatus = ModelStatus.ACTIVE


@dataclass(frozen=True)
class Transition:
    action: Action
    source: MarketState
    target: MarketState


@dataclass(frozen=True)
class Counterexample:
    state: MarketState
    trace: Tuple[Action, ...]
    reason: str


@dataclass(frozen=True)
class ExplorationResult:
    states: Tuple[MarketState, ...]
    transitions: Tuple[Transition, ...]
    counterexamples: Tuple[Counterexample, ...]
    max_depth: int


def invariant_violations(state: MarketState) -> Tuple[str, ...]:
    """Return safety violations in a candidate abstract global state."""
    problems: List[str] = []
    if state.transaction_stage not in range(5):
        problems.append("transaction stage must be a prefix from 0 through 4")
    if state.listing is ListingStatus.DELISTED and state.relist_approved:
        # Approval is retained as a historical fact only while delisted; it is
        # not itself unsafe. The invariant is instead checked at RELIST guard.
        pass
    if state.model_status is ModelStatus.ACTIVE and state.model_status is not ModelStatus.ACTIVE:
        problems.append("model status is inconsistent")
    return tuple(problems)


def successors(state: MarketState) -> Tuple[Tuple[Action, MarketState], ...]:
    """Return every permitted one-step transition from state.

    Delisting requires suspension. Re-listing requires both eligibility and
    approval. Order progression requires the instrument to be listed. Model
    activation requires a tested and approved revision.
    """
    out: List[Tuple[Action, MarketState]] = []

    def add(action: Action, **changes: object) -> None:
        from dataclasses import replace
        out.append((action, replace(state, **changes)))

    if state.listing is ListingStatus.LISTED:
        add(Action.SUSPEND, listing=ListingStatus.SUSPENDED)
    if state.listing is ListingStatus.SUSPENDED:
        add(Action.RESUME, listing=ListingStatus.LISTED)
        add(Action.DELIST, listing=ListingStatus.DELISTED,
            relist_eligible=False, relist_approved=False)
    if state.listing is ListingStatus.DELISTED:
        if not state.relist_eligible:
            add(Action.MARK_RELIST_ELIGIBLE, relist_eligible=True)
        if state.relist_eligible and not state.relist_approved:
            add(Action.APPROVE_RELISTING, relist_approved=True)
        if state.relist_eligible and state.relist_approved:
            add(Action.RELIST, listing=ListingStatus.LISTED,
                relist_eligible=False, relist_approved=False)

    if state.listing is ListingStatus.LISTED:
        if state.transaction_stage == 0:
            add(Action.SUBMIT_ORDER, transaction_stage=1)
        elif state.transaction_stage == 1:
            add(Action.EXECUTE, transaction_stage=2)
        elif state.transaction_stage == 2:
            add(Action.CLEAR, transaction_stage=3)
        elif state.transaction_stage == 3:
            add(Action.SETTLE, transaction_stage=4)

    if state.model_status is ModelStatus.ACTIVE:
        add(Action.BEGIN_MODEL_REVISION, model_status=ModelStatus.REVISING)
    elif state.model_status is ModelStatus.REVISING:
        add(Action.TEST_MODEL_REVISION, model_status=ModelStatus.TESTED)
    elif state.model_status is ModelStatus.TESTED:
        add(Action.APPROVE_MODEL_REVISION, model_status=ModelStatus.APPROVED)
    elif state.model_status is ModelStatus.APPROVED:
        add(Action.ACTIVATE_MODEL_REVISION, model_status=ModelStatus.ACTIVE)

    return tuple(out)


def explore(
    initial: Optional[MarketState] = None,
    *,
    max_depth: int = 8,
    invariant: Callable[[MarketState], bool] = lambda state: not invariant_violations(state),
) -> ExplorationResult:
    """Explore all unique states reachable within max_depth.

    Breadth-first search retains the shortest trace to each state. If an
    invariant fails, the corresponding shortest counterexample trace is saved.
    A nonnegative depth is required; depth zero checks only the initial state.
    """
    if max_depth < 0:
        raise ValueError("max_depth must be nonnegative")
    start = initial or MarketState()
    queue = deque([(start, tuple(), 0)])
    shortest_trace: Dict[MarketState, Tuple[Action, ...]] = {start: tuple()}
    all_transitions: Dict[Tuple[MarketState, Action, MarketState], Transition] = {}
    failures: List[Counterexample] = []

    while queue:
        state, trace, depth = queue.popleft()
        if not invariant(state):
            failures.append(Counterexample(state, trace, "invariant returned false"))
        if depth >= max_depth:
            continue
        for action, target in successors(state):
            transition = Transition(action, state, target)
            all_transitions[(state, action, target)] = transition
            if target not in shortest_trace:
                next_trace = trace + (action,)
                shortest_trace[target] = next_trace
                queue.append((target, next_trace, depth + 1))

    # Deduplicate violations by state; BFS ensures each stored trace is shortest.
    unique_failures: Dict[MarketState, Counterexample] = {}
    for failure in failures:
        unique_failures.setdefault(failure.state, failure)
    return ExplorationResult(
        states=tuple(shortest_trace),
        transitions=tuple(all_transitions.values()),
        counterexamples=tuple(unique_failures.values()),
        max_depth=max_depth,
    )
