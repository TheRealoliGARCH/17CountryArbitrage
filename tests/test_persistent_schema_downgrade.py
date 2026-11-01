import json
import tempfile
import unittest
from pathlib import Path

from market17.event_processor import Event, EventKind
from market17.persistent import PersistentEventProcessor


def event_dict(event_id="event-1"):
    return {
        "event_id": event_id,
        "timestamp": 1,
        "sequence": 1,
        "instrument_id": "ABC",
        "kind": EventKind.SUSPEND.value,
        "transaction_id": "",
    }


class TestJournalSchemaDowngrade(unittest.TestCase):
    def test_legacy_record_after_v3_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            writer = PersistentEventProcessor(journal)
            writer.process_batch([
                Event("first", 1, 1, "ABC", EventKind.SUSPEND, "")
            ])
            records = [json.loads(line) for line in journal.read_text().splitlines()]
            records.append({"version": 1, "events": [event_dict("legacy")]})
            journal.write_text(
                "".join(json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n"
                        for record in records),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "line 2.*schema downgrade"):
                PersistentEventProcessor(journal)

    def test_v2_record_after_v3_fails_closed_even_with_valid_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            writer = PersistentEventProcessor(journal)
            writer.process_batch([
                Event("first", 1, 1, "ABC", EventKind.SUSPEND, "")
            ])
            v2 = {
                "version": 2,
                "record_index": 2,
                "events": [event_dict("legacy-v2")],
            }
            v2["sha512"] = PersistentEventProcessor._digest(v2)
            with journal.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(v2, separators=(",", ":"), sort_keys=True) + "\n")
            with self.assertRaisesRegex(ValueError, "line 2.*schema downgrade"):
                PersistentEventProcessor(journal)

    def test_boolean_schema_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            journal.write_text(
                json.dumps({"version": True, "events": []}) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "line 1.*unsupported record version"):
                PersistentEventProcessor(journal)


if __name__ == "__main__":
    unittest.main()
