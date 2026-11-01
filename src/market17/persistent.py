"""JSONL-backed event batches with deterministic, integrity-checked replay.

New records use SHA-512 digests, monotonic indices, and a hash chain.
Legacy version-1 and version-2 records remain readable for compatibility.
This is a local research store, not a distributed or exchange-grade journal.
"""
from __future__ import annotations

import copy
import hashlib
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
        if not isinstance(record, dict):
            raise ValueError("event must be an object")
        return Event(
            event_id=record["event_id"],
            timestamp=int(record["timestamp"]),
            sequence=int(record["sequence"]),
            instrument_id=record["instrument_id"],
            kind=EventKind(record["kind"]),
            transaction_id=record.get("transaction_id", ""),
        )

    @staticmethod
    def _canonical_bytes(payload: dict) -> bytes:
        return json.dumps(
            payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False
        ).encode("utf-8")

    @classmethod
    def _digest(cls, payload: dict) -> str:
        """Hash a v2/v3 record except its own digest field."""
        unsigned = {key: value for key, value in payload.items() if key != "sha512"}
        return hashlib.sha512(cls._canonical_bytes(unsigned)).hexdigest()

    @classmethod
    def _legacy_anchor(cls, payload: dict) -> str:
        """Derive a deterministic chain anchor for a v1 record without a digest."""
        return hashlib.sha512(cls._canonical_bytes(payload)).hexdigest()

    def _read_validated_batches(self):
        """Validate all records and return (batches, final chain digest)."""
        parsed_batches = []
        expected_index = 1
        previous_digest = "0" * 128
        with self.path.open("rb") as stream:
            for line_number, raw_line in enumerate(stream, start=1):
                if not raw_line.endswith(b"\n"):
                    raise ValueError(
                        f"incomplete event journal record on line {line_number}"
                    )
                try:
                    payload = json.loads(raw_line)
                    if not isinstance(payload, dict):
                        raise ValueError("record must be an object")
                    version = payload.get("version")
                    if version == 1:
                        if not isinstance(payload.get("events"), list):
                            raise ValueError("missing events list")
                        current_digest = self._legacy_anchor(payload)
                    elif version == 2:
                        if payload.get("record_index") != expected_index:
                            raise ValueError("unexpected record index")
                        if not isinstance(payload.get("events"), list):
                            raise ValueError("missing events list")
                        digest = payload.get("sha512")
                        if not isinstance(digest, str) or digest != self._digest(payload):
                            raise ValueError("journal digest mismatch")
                        current_digest = digest
                    elif version == 3:
                        if payload.get("record_index") != expected_index:
                            raise ValueError("unexpected record index")
                        if not isinstance(payload.get("events"), list):
                            raise ValueError("missing events list")
                        if payload.get("previous_sha512") != previous_digest:
                            raise ValueError("journal chain mismatch")
                        digest = payload.get("sha512")
                        if not isinstance(digest, str) or digest != self._digest(payload):
                            raise ValueError("journal digest mismatch")
                        current_digest = digest
                    else:
                        raise ValueError("unsupported record version")
                    events = [self._dict_to_event(item) for item in payload["events"]]
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"invalid event journal record on line {line_number}: {exc}"
                    ) from exc
                parsed_batches.append(events)
                previous_digest = current_digest
                expected_index += 1
        return parsed_batches, previous_digest

    def _recover(self) -> None:
        """Validate the entire journal, then replay atomically into processor state."""
        parsed_batches, _ = self._read_validated_batches()
        staged_processor = copy.deepcopy(self.processor)
        for events in parsed_batches:
            staged_processor.process_batch(events)
        self.processor.__dict__.clear()
        self.processor.__dict__.update(staged_processor.__dict__)

    def process_batch(self, events: Iterable[Event]):
        """Append a hash-chained record, then apply it; undo append on exceptions."""
        batch = list(events)
        if any(not event.event_id or not event.instrument_id for event in batch):
            raise ValueError("event_id and instrument_id must be non-empty")
        ids = [event.event_id for event in batch]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event_id within batch")

        if self.path.exists() and self.path.stat().st_size:
            _, previous_digest = self._read_validated_batches()
            with self.path.open("rb") as stream:
                record_index = sum(1 for _ in stream) + 1
        else:
            previous_digest = "0" * 128
            record_index = 1

        payload = {
            "version": 3,
            "record_index": record_index,
            "previous_sha512": previous_digest,
            "events": [self._event_to_dict(event) for event in batch],
        }
        payload["sha512"] = self._digest(payload)
        encoded = self._canonical_bytes(payload) + b"\n"
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
