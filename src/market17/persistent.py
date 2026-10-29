"""JSONL-backed event batches with deterministic replay.

This is a local research store, not a distributed or exchange-grade journal.
Each batch is written and fsynced before it is applied in memory. On ordinary
processing exceptions, the appended record is truncated and the processor's
batch rollback restores its prior state.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, Optional

from .event_processor import Event, EventKind, EventProcessor


class PersistentEventProcessor:
    """Persist event batches locally and rebuild processor state by replay."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        processor: Optional[EventProcessor] = None,
        *,
        recover: bool = True,
    ) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.processor = processor if processor is not None else EventProcessor()
        if recover and self.path.exists():
            self._recover()

    @staticmethod
    def _event_to_dict(event: Event) -> dict:
        return {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "sequence": event.sequence,
            "instrument_id": event.instrument_id,
            "kind": event.kind.value,
            "transaction_id": event.transaction_id,
        }

    @staticmethod
    def _dict_to_event(record: dict) -> Event:
        return Event(
            event_id=record["event_id"],
            timestamp=int(record["timestamp"]),
            sequence=int(record["sequence"]),
            instrument_id=record["instrument_id"],
            kind=EventKind(record["kind"]),
            transaction_id=record.get("transaction_id", ""),
        )

    def _recover(self) -> None:
        """Replay every complete batch; malformed records fail closed."""
        with self.path.open("rb") as stream:
            for line_number, raw_line in enumerate(stream, start=1):
                if not raw_line.strip():
                    continue
                try:
                    payload = json.loads(raw_line)
                    if payload.get("version") != 1 or not isinstance(payload.get("events"), list):
                        raise ValueError("unsupported record version or missing events list")
                    events = [self._dict_to_event(item) for item in payload["events"]]
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"invalid event journal record on line {line_number}"
                    ) from exc
                self.processor.process_batch(events)

    def process_batch(self, events: Iterable[Event]):
        """Durably append one batch, then apply it; undo the append on exceptions."""
        batch = list(events)
        # Let the processor perform its canonical validation before touching disk.
        if any(not event.event_id or not event.instrument_id for event in batch):
            raise ValueError("event_id and instrument_id must be non-empty")
        ids = [event.event_id for event in batch]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event_id within batch")

        payload = {
            "version": 1,
            "events": [self._event_to_dict(event) for event in batch],
        }
        encoded = (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode("utf-8")
        with self.path.open("a+b") as stream:
            stream.seek(0, os.SEEK_END)
            start = stream.tell()
            try:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
                result = self.processor.process_batch(batch)
            except Exception:
                stream.seek(start)
                stream.truncate()
                stream.flush()
                os.fsync(stream.fileno())
                raise
        return result
