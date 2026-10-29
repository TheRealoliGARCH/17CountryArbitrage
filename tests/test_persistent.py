import tempfile
import unittest
from pathlib import Path

from market17.event_processor import Event, EventKind, EventProcessor
from market17.persistent import PersistentEventProcessor


def event(event_id, kind, *, instrument="ABC", tx="", timestamp=1, sequence=1):
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        sequence=sequence,
        instrument_id=instrument,
        kind=kind,
        transaction_id=tx,
    )


class TestPersistentEventProcessor(unittest.TestCase):
    def test_recovery_reconstructs_transaction_and_audit_state(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            first = PersistentEventProcessor(journal)
            first.process_batch([
                event("submit", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=1),
                event("execute", EventKind.EXECUTION_CONFIRMED, tx="tx-1", timestamp=2),
            ])
            first.process_batch([
                event("clear", EventKind.CLEARING_CONFIRMED, tx="tx-1", timestamp=3),
                event("settle", EventKind.SETTLEMENT_CONFIRMED, tx="tx-1", timestamp=4),
            ])

            recovered = PersistentEventProcessor(journal)
            self.assertTrue(recovered.processor.invariants_hold())
            tx = recovered.processor.transactions[("ABC", "tx-1")]
            self.assertTrue(all((tx.order_submitted, tx.executed, tx.cleared, tx.settled)))
            self.assertEqual(
                [entry.event_id for entry in recovered.processor.audit_log],
                ["submit", "execute", "clear", "settle"],
            )
            self.assertEqual(recovered.processor.last_event_order["ABC"], (4, 1, "settle"))

    def test_replay_preserves_batch_ordering_and_suspension_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            processor = PersistentEventProcessor(journal)
            processor.process_batch([
                event("order", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=2),
                event("suspend", EventKind.SUSPEND, timestamp=1),
            ])
            recovered = PersistentEventProcessor(journal)
            outcomes = {entry.event_id: entry.outcome for entry in recovered.processor.audit_log}
            self.assertEqual(outcomes, {"suspend": "applied", "order": "blocked"})
            self.assertTrue(recovered.processor.instruments["ABC"].suspended)

    def test_failed_processing_removes_uncommitted_journal_record(self):
        class FailingProcessor(EventProcessor):
            def _apply(self, item):
                if item.event_id == "explode":
                    raise RuntimeError("injected failure")
                return super()._apply(item)

        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            persistent = PersistentEventProcessor(journal, processor=FailingProcessor())
            with self.assertRaisesRegex(RuntimeError, "injected failure"):
                persistent.process_batch([
                    event("suspend", EventKind.SUSPEND, timestamp=1),
                    event("explode", EventKind.RESUME, timestamp=2),
                ])
            self.assertEqual(journal.read_bytes(), b"")
            self.assertFalse(persistent.processor.instruments)

    def test_duplicate_event_replay_remains_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            persistent = PersistentEventProcessor(journal)
            item = event("suspend", EventKind.SUSPEND)
            persistent.process_batch([item])
            persistent.process_batch([item])
            recovered = PersistentEventProcessor(journal)
            outcomes = [entry.outcome for entry in recovered.processor.audit_log]
            self.assertEqual(outcomes, ["applied", "ignored"])
            self.assertEqual(len(recovered.processor.processed_event_ids), 1)

    def test_malformed_journal_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "events.jsonl"
            journal.write_text('{"version":1,"events": [\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 1"):
                PersistentEventProcessor(journal)


if __name__ == "__main__":
    unittest.main()
