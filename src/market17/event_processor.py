"""Deterministic, in-memory event processor for the 17-State Market.

This is a research reference implementation, not an exchange or settlement
gateway. State and audit entries are in memory only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Set, Tuple


class EventKind(str, Enum):
    SUSPEND = "suspend"
    RESUME = "resume"
    SUBMIT_ORDER = "submit_order"
    EXECUTION_CONFIRMED = "execution_confirmed"
    CLEARING_CONFIRMED = "clearing_confirmed"
    SETTLEMENT_CONFIRMED = "settlement_confirmed"


@dataclass(frozen=True)
class Event:
    event_id: str
    timestamp: int
    sequence: int
    instrument_id: str
    kind: EventKind
    transaction_id: str = ""


@dataclass
class InstrumentState:
    suspended: bool = False
    listing_status: str = "listed"


@dataclass
class TransactionState:
    order_submitted: bool = False
    executed: bool = False
    cleared: bool = False
    settled: bool = False

    def is_reachable(self) -> bool:
        """Whether the flags describe a prefix of the normal transaction route."""
        return (
            (not self.executed or self.order_submitted)
            and (not self.cleared or self.executed)
            and (not self.settled or self.cleared)
        )


@dataclass(frozen=True)
class AuditEntry:
    event_id: str
    instrument_id: str
    transaction_id: str
    kind: EventKind
    outcome: str
    detail: str


@dataclass
class EventProcessor:
    """Apply timestamp-ordered events and enforce core safety invariants.

    Events are ordered by (timestamp, sequence, event_id). The same ordering
    applies to controls and ordinary events: a suspension only affects events
    at or after its position in that order. Events older than an instrument's
    last accepted ordering key are rejected as late; the processor never
    silently rewinds state. A rejected/blocked event ID is consumed for
    idempotency; a corrected retry must use a new event ID.
    """

    instruments: Dict[str, InstrumentState] = field(default_factory=dict)
    transactions: Dict[Tuple[str, str], TransactionState] = field(default_factory=dict)
    processed_event_ids: Set[str] = field(default_factory=set)
    audit_log: List[AuditEntry] = field(default_factory=list)
    last_event_order: Dict[str, Tuple[int, int, str]] = field(default_factory=dict)

    def _instrument(self, instrument_id: str) -> InstrumentState:
        if not instrument_id:
            raise ValueError("instrument_id must be non-empty")
        return self.instruments.setdefault(instrument_id, InstrumentState())

    def process_batch(self, events: Iterable[Event]) -> List[AuditEntry]:
        """Validate a batch and process it deterministically.

        Duplicate IDs within a batch fail before mutation. Previously seen IDs
        are no-ops. Valid events are globally sorted by event time, sequence,
        and ID, with no special control-event priority.
        """
        batch = list(events)
        if any(not e.event_id or not e.instrument_id for e in batch):
            raise ValueError("event_id and instrument_id must be non-empty")
        ids = [e.event_id for e in batch]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event_id within batch")

        ordered = sorted(batch, key=lambda e: (e.timestamp, e.sequence, e.event_id))
        created: List[AuditEntry] = []
        for event in ordered:
            if event.event_id in self.processed_event_ids:
                entry = self._entry(event, "ignored", "event ID already processed")
            else:
                key = (event.timestamp, event.sequence, event.event_id)
                previous = self.last_event_order.get(event.instrument_id)
                if previous is not None and key < previous:
                    entry = self._entry(
                        event, "rejected",
                        "late event precedes the instrument's accepted event watermark",
                    )
                else:
                    entry = self._apply(event)
                    self.last_event_order[event.instrument_id] = key
                self.processed_event_ids.add(event.event_id)
            self.audit_log.append(entry)
            created.append(entry)
        return created

    def invariants_hold(self) -> bool:
        """Check transaction reachability and consistency of the event-ID ledger."""
        return all(tx.is_reachable() for tx in self.transactions.values())

    def _apply(self, event: Event) -> AuditEntry:
        instrument = self._instrument(event.instrument_id)
        tx_key = (event.instrument_id, event.transaction_id)

        if event.kind is EventKind.SUSPEND:
            instrument.suspended = True
            return self._entry(event, "applied", "instrument suspended")
        if event.kind is EventKind.RESUME:
            instrument.suspended = False
            return self._entry(event, "applied", "instrument resumed")

        if event.kind is EventKind.SUBMIT_ORDER:
            if instrument.suspended:
                return self._entry(event, "blocked", "instrument is suspended")
            if instrument.listing_status != "listed":
                return self._entry(event, "blocked", "instrument is not listed")
            if not event.transaction_id:
                return self._entry(event, "rejected", "transaction_id is required")
            tx = self.transactions.setdefault(tx_key, TransactionState())
            if tx.order_submitted:
                return self._entry(event, "ignored", "order already submitted")
            tx.order_submitted = True
            return self._entry(event, "applied", "order submitted")

        if not event.transaction_id:
            return self._entry(event, "rejected", "transaction_id is required")
        tx = self.transactions.get(tx_key)
        if tx is None or not tx.order_submitted:
            return self._entry(event, "blocked", "no submitted order for transaction")

        if event.kind is EventKind.EXECUTION_CONFIRMED:
            if tx.executed:
                return self._entry(event, "ignored", "execution already recorded")
            tx.executed = True
            return self._entry(event, "applied", "execution confirmed")
        if event.kind is EventKind.CLEARING_CONFIRMED:
            if not tx.executed:
                return self._entry(event, "blocked", "execution not confirmed")
            if tx.cleared:
                return self._entry(event, "ignored", "clearing already recorded")
            tx.cleared = True
            return self._entry(event, "applied", "clearing confirmed")
        if event.kind is EventKind.SETTLEMENT_CONFIRMED:
            if not tx.cleared:
                return self._entry(event, "blocked", "clearing not confirmed")
            if tx.settled:
                return self._entry(event, "ignored", "settlement already recorded")
            tx.settled = True
            return self._entry(event, "applied", "settlement confirmed")
        return self._entry(event, "rejected", "unsupported event kind")

    @staticmethod
    def _entry(event: Event, outcome: str, detail: str) -> AuditEntry:
        return AuditEntry(
            event.event_id, event.instrument_id, event.transaction_id,
            event.kind, outcome, detail,
        )
