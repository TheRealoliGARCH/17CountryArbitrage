import unittest

from market17.event_processor import Event, EventKind, EventProcessor


def event(event_id, kind, *, instrument="ABC", tx="", timestamp=1, sequence=1):
    return Event(
        event_id=event_id,
        timestamp=timestamp,
        sequence=sequence,
        instrument_id=instrument,
        kind=kind,
        transaction_id=tx,
    )


class TestEventProcessor(unittest.TestCase):
    def test_suspension_has_priority_over_order_in_same_batch(self):
        processor = EventProcessor()
        results = processor.process_batch([
            event("order-1", EventKind.SUBMIT_ORDER, tx="tx-1"),
            event("suspend-1", EventKind.SUSPEND),
        ])
        outcomes = {entry.event_id: entry.outcome for entry in results}
        self.assertEqual(outcomes["suspend-1"], "applied")
        self.assertEqual(outcomes["order-1"], "blocked")
        self.assertFalse(processor.transactions)

    def test_different_instruments_are_scoped_independently(self):
        processor = EventProcessor()
        processor.process_batch([
            event("suspend-a", EventKind.SUSPEND, instrument="A"),
            event("order-b", EventKind.SUBMIT_ORDER, instrument="B", tx="tx-b"),
        ])
        self.assertTrue(processor.instruments["A"].suspended)
        self.assertTrue(processor.transactions[("B", "tx-b")].order_submitted)

    def test_transaction_requires_execution_before_clearing(self):
        processor = EventProcessor()
        processor.process_batch([
            event("submit", EventKind.SUBMIT_ORDER, tx="tx-1"),
        ])
        result = processor.process_batch([
            event("clear-early", EventKind.CLEARING_CONFIRMED, tx="tx-1"),
        ])[0]
        self.assertEqual(result.outcome, "blocked")
        self.assertFalse(processor.transactions[("ABC", "tx-1")].cleared)

    def test_transaction_progression(self):
        processor = EventProcessor()
        results = processor.process_batch([
            event("submit", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=1),
            event("execute", EventKind.EXECUTION_CONFIRMED, tx="tx-1", timestamp=2),
            event("clear", EventKind.CLEARING_CONFIRMED, tx="tx-1", timestamp=3),
            event("settle", EventKind.SETTLEMENT_CONFIRMED, tx="tx-1", timestamp=4),
        ])
        self.assertTrue(all(entry.outcome == "applied" for entry in results))
        tx = processor.transactions[("ABC", "tx-1")]
        self.assertTrue(tx.order_submitted)
        self.assertTrue(tx.executed)
        self.assertTrue(tx.cleared)
        self.assertTrue(tx.settled)

    def test_settlement_cannot_precede_clearing(self):
        processor = EventProcessor()
        processor.process_batch([
            event("submit", EventKind.SUBMIT_ORDER, tx="tx-1"),
            event("execute", EventKind.EXECUTION_CONFIRMED, tx="tx-1"),
        ])
        result = processor.process_batch([
            event("settle-early", EventKind.SETTLEMENT_CONFIRMED, tx="tx-1"),
        ])[0]
        self.assertEqual(result.outcome, "blocked")
        self.assertFalse(processor.transactions[("ABC", "tx-1")].settled)

    def test_duplicate_event_id_is_idempotent(self):
        processor = EventProcessor()
        first = event("submit-1", EventKind.SUBMIT_ORDER, tx="tx-1")
        processor.process_batch([first])
        second = processor.process_batch([first])[0]
        self.assertEqual(second.outcome, "ignored")
        self.assertTrue(processor.transactions[("ABC", "tx-1")].order_submitted)
        self.assertEqual(len(processor.transactions), 1)

    def test_duplicate_ids_in_one_batch_rejected_before_processing(self):
        processor = EventProcessor()
        with self.assertRaises(ValueError):
            processor.process_batch([
                event("same", EventKind.SUSPEND),
                event("same", EventKind.SUBMIT_ORDER, tx="tx-1"),
            ])
        self.assertFalse(processor.instruments)

    def test_batch_order_is_deterministic(self):
        first = [
            event("order", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=1),
            event("suspend", EventKind.SUSPEND, timestamp=9),
        ]
        second = list(reversed(first))
        p1, p2 = EventProcessor(), EventProcessor()
        out1 = [(x.event_id, x.outcome) for x in p1.process_batch(first)]
        out2 = [(x.event_id, x.outcome) for x in p2.process_batch(second)]
        self.assertEqual(out1, out2)

    def test_order_blocked_for_nonlisted_instrument(self):
        processor = EventProcessor()
        processor.instruments["ABC"] = type("Instrument", (), {
            "suspended": False, "listing_status": "delisted"
        })()
        result = processor.process_batch([
            event("order", EventKind.SUBMIT_ORDER, tx="tx-1"),
        ])[0]
        self.assertEqual(result.outcome, "blocked")


if __name__ == "__main__":
    unittest.main()
