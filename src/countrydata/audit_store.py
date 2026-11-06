"""Append-only SQLite provenance and quarantine store (standard library only)."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable

from .validation import ValidationResult


SCHEMA = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    accepted_count INTEGER NOT NULL,
    quarantined_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_records (
    raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES ingestion_runs(run_id),
    source_name TEXT NOT NULL,
    source_series_id TEXT NOT NULL,
    source_vintage TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    UNIQUE(run_id, payload_sha256)
);
CREATE TABLE IF NOT EXISTS validation_records (
    validation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_id INTEGER NOT NULL REFERENCES raw_records(raw_id),
    accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
    observation_json TEXT NOT NULL,
    issues_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_records_source
    ON raw_records(source_name, source_series_id, source_vintage);
CREATE INDEX IF NOT EXISTS idx_validation_records_accepted
    ON validation_records(accepted);
CREATE TRIGGER IF NOT EXISTS raw_records_no_update
BEFORE UPDATE ON raw_records BEGIN
    SELECT RAISE(ABORT, 'raw_records are append-only');
END;
CREATE TRIGGER IF NOT EXISTS raw_records_no_delete
BEFORE DELETE ON raw_records BEGIN
    SELECT RAISE(ABORT, 'raw_records are append-only');
END;
CREATE TRIGGER IF NOT EXISTS validation_records_no_update
BEFORE UPDATE ON validation_records BEGIN
    SELECT RAISE(ABORT, 'validation_records are append-only');
END;
CREATE TRIGGER IF NOT EXISTS validation_records_no_delete
BEFORE DELETE ON validation_records BEGIN
    SELECT RAISE(ABORT, 'validation_records are append-only');
END;
"""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _observation_payload(result: ValidationResult) -> dict[str, Any]:
    item = result.observation
    payload = asdict(item)
    for key, value in payload.items():
        if isinstance(value, (datetime,)):
            payload[key] = value.isoformat()
        elif hasattr(value, "isoformat") and value is not None:
            payload[key] = value.isoformat()
    return payload


class AuditStore:
    """Persist raw source payloads and validation outcomes in an append-only DB."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        with self._connect() as connection:
            connection.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def record_batch(
        self,
        raw_payloads: Iterable[dict[str, Any]],
        results: Iterable[ValidationResult],
        started_at: datetime | None = None,
    ) -> int:
        """Atomically store corresponding raw payloads and validation results.

        The payload and result iterables must be in the same order and have equal
        lengths. SHA-256 is computed over canonical UTF-8 JSON, not source bytes.
        """
        raw_items = list(raw_payloads)
        validated = list(results)
        if len(raw_items) != len(validated):
            raise ValueError("raw_payloads and results must have equal lengths")
        timestamp = started_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("started_at must be timezone-aware")

        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO ingestion_runs(started_at, record_count, accepted_count, quarantined_count) "
                "VALUES (?, ?, ?, ?)",
                (
                    timestamp.isoformat(), len(validated),
                    sum(result.accepted for result in validated),
                    sum(result.quarantined for result in validated),
                ),
            )
            run_id = int(cursor.lastrowid)
            for payload, result in zip(raw_items, validated):
                if not isinstance(payload, dict):
                    raise ValueError("each raw payload must be a dictionary")
                payload_json = _canonical_json(payload)
                checksum = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
                observation = result.observation
                raw_cursor = connection.execute(
                    "INSERT INTO raw_records(run_id, source_name, source_series_id, source_vintage, "
                    "retrieved_at, payload_json, payload_sha256) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id, observation.source_name, observation.source_series_id,
                        observation.source_vintage, observation.retrieved_at.isoformat(),
                        payload_json, checksum,
                    ),
                )
                issues = [asdict(issue) for issue in result.issues]
                connection.execute(
                    "INSERT INTO validation_records(raw_id, accepted, observation_json, issues_json) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        int(raw_cursor.lastrowid), int(result.accepted),
                        _canonical_json(_observation_payload(result)),
                        _canonical_json(issues),
                    ),
                )
            return run_id

    def run_summary(self, run_id: int) -> dict[str, int | str]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT started_at, record_count, accepted_count, quarantined_count "
                "FROM ingestion_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown ingestion run: {run_id}")
        return {
            "started_at": row[0], "record_count": row[1],
            "accepted_count": row[2], "quarantined_count": row[3],
        }

    def quarantined_records(self, run_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT r.raw_id, r.payload_json, r.payload_sha256, v.observation_json, v.issues_json "
                "FROM raw_records r JOIN validation_records v ON v.raw_id = r.raw_id "
                "WHERE r.run_id = ? AND v.accepted = 0 ORDER BY r.raw_id",
                (run_id,),
            ).fetchall()
        return [
            {
                "raw_id": row[0], "payload": json.loads(row[1]),
                "payload_sha256": row[2], "observation": json.loads(row[3]),
                "issues": json.loads(row[4]),
            }
            for row in rows
        ]
