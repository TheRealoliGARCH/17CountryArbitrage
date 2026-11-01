import tempfile
import unittest
from pathlib import Path

from market17.event_processor import Event, EventKind
from market17.persistent import PersistentEventProcessor


def suspend(event_id, timestamp):
    return Event(event_id, timestamp, 1, "ABC", EventKind.SUSPEND, "")


class TestJournalWriterLock(unittest.TestCase):
    def test_stale_writer_is_rejected_after_another_writer_commits(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            writer_a = PersistentEventProcessor(journal)
            writer_b = PersistentEventProcessor(journal)

            writer_a.process_batch([suspend("first", 1)])
            before = journal.read_bytes()

            with self.assertRaisesRegex(RuntimeError, "journal changed since this processor was opened"):
                writer_b.process_batch([suspend("second", 2)])

            self.assertEqual(journal.read_bytes(), before)
            recovered = PersistentEventProcessor(journal)
            self.assertEqual(
                [entry.event_id for entry in recovered.processor.audit_log],
                ["first"],
            )

    def test_reopened_writer_can_continue_after_previous_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            first = PersistentEventProcessor(journal)
            first.process_batch([suspend("first", 1)])

            reopened = PersistentEventProcessor(journal)
            reopened.process_batch([suspend("second", 2)])

            recovered = PersistentEventProcessor(journal)
            self.assertEqual(
                [entry.event_id for entry in recovered.processor.audit_log],
                ["first", "second"],
            )


if __name__ == "__main__":
    unittest.main()
