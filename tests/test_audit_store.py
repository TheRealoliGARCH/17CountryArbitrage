from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from countrydata.audit_store import AuditStore
from countrydata.panel import load_country_panel
from countrydata.schema import Observation
from countrydata.validation import validate_observation


ROOT = Path(__file__).resolve().parents[1]
PANEL = load_country_panel(ROOT / "config" / "country_panel.csv")


def payload(**overrides):
    data = {
        "country_code": "CH", "instrument_id": "CH-GOV-10Y",
        "instrument_type": "sovereign_bond", "measure": "mid_yield",
        "observation_time": "2026-11-06T09:00:00+01:00",
        "availability_time": "2026-11-06T09:00:01+01:00",
        "value": -0.25, "unit": "percent_per_annum", "currency_code": "CHF",
        "source_name": "Example Source", "source_series_id": "SERIES-1",
        "retrieved_at": "2026-11-06T09:01:00+01:00",
        "source_vintage": "release-1", "quality_status": "valid",
    }
    data.update(overrides)
    return data


class TestAuditStore(unittest.TestCase):
    def test_persists_provenance_and_quarantine_atomically(self):
        good = payload()
        bad = payload(country_code="ZZ", source_series_id="SERIES-2")
        results = [
            validate_observation(Observation.from_mapping(good), PANEL),
            validate_observation(Observation.from_mapping(bad), PANEL),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.sqlite3"
            store = AuditStore(path)
            run_id = store.record_batch(
                [good, bad], results,
                datetime(2026, 11, 6, 9, 2, tzinfo=timezone.utc),
            )
            self.assertEqual(store.run_summary(run_id)["record_count"], 2)
            self.assertEqual(store.run_summary(run_id)["accepted_count"], 1)
            quarantined = store.quarantined_records(run_id)
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(quarantined[0]["payload"], bad)
            expected = hashlib.sha256(
                json.dumps(bad, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            ).hexdigest()
            self.assertEqual(quarantined[0]["payload_sha256"], expected)
            self.assertIn("unknown_country", {issue["code"] for issue in quarantined[0]["issues"]})

    def test_mismatched_batch_lengths_fail_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AuditStore(Path(directory) / "audit.sqlite3")
            with self.assertRaises(ValueError):
                store.record_batch([], [validate_observation(Observation.from_mapping(payload()), PANEL)])
            with sqlite3.connect(store.path) as connection:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM ingestion_runs").fetchone()[0], 0)

    def test_raw_records_are_append_only(self):
        item = payload()
        result = validate_observation(Observation.from_mapping(item), PANEL)
        with tempfile.TemporaryDirectory() as directory:
            store = AuditStore(Path(directory) / "audit.sqlite3")
            run_id = store.record_batch([item], [result])
            with sqlite3.connect(store.path) as connection:
                raw_id = connection.execute(
                    "SELECT raw_id FROM raw_records WHERE run_id = ?", (run_id,)
                ).fetchone()[0]
                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute("DELETE FROM raw_records WHERE raw_id = ?", (raw_id,))


if __name__ == "__main__":
    unittest.main()
