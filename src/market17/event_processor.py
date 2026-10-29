"""Deterministic, in-memory event processor for the 17-State Market.

This is a research reference implementation. It is not connected to an exchange
or payment/settlement infrastructure. Events are processed atomically in memory
and an append-only audit list is retained for the lifetime of the processor.
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


# Lower number is higher priority. Suspension/resumption controls are handled
# before ordinary orders in the same batch, regardless of their input order.
PRIORITY: Dict[EventKind, int] = {
    EventKind.SUSPEND: 0,
    EventKind.RESUME: 0,
    EventKind.EXECUTION_CONFIRMED: 1,
    EventKind.CLEARING_CONFIRMED: 1,
    EventKind.SETTLEMENT_CONFIRMED: 1,
    EventKind.SUBMIT_ORDER: 2,
}


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
    """Apply events in deterministic order and enforce core safety guards."""

    instruments: Dict[str, InstrumentState] = field(default_factory=dict)
    transactions: Dict[Tuple[str, str], TransactionState] = field(default_factory=dict)
    processed_event_ids: Set[str] = field(default_factory=set)
    audit_log: List[AuditEntry] = field(default_factory=list)

    def _instrument(self, instrument_id: str) -> InstrumentState:
        if not instrument_id:
            raise ValueError("instrument_id must be non-empty")
        return self.instruments.setdefault(instrument_id, InstrumentState())

    def process_batch(self, events: Iterable[Event]) -> List[AuditEntry]:
        """Process one batch by priority, timestamp, sequence, and event ID.

        The method validates the full batch before applying any event. Duplicate
        IDs within the batch are rejected; IDs already processed are recorded
        as duplicate no-ops. Batch ordering is deterministic for equal inputs.
        """
        batch = list(events)
        if any(not e.event_id or not e.instrument_id for e in batch):
            raise ValueError("event_id and instrument_id must be non-empty")
        ids = [e.event_id for e in batch]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event_id within batch")

        ordered = sorted(
            batch,
            key=lambda e: (
                PRIORITY[e.kind], e.timestamp, e.sequence, e.event_id
            ),
        )
        created: List[AuditEntry] = []
        for event in ordered:
            if event.event_id in self.processed_event_ids:
                entry = AuditEntry(
                    event.event_id, event.instrument_id, event.transaction_id,
                    event.kind, "ignored", "event ID already processed",
                )
                self.audit_log.append(entry)
                created.append(entry)
                continue
            entry = self._apply(event)
            self.processed_event_ids.add(event.event_id)
            self.audit_log.append(entry)
            created.append(entry)
        return created

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
