import itertools
import unittest

from market17.event_processor import (
    Event, EventKind, EventProcessor, TransactionState,
)


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
    def test_suspension_blocks_later_order_in_same_batch(self):
        processor = EventProcessor()
        results = processor.process_batch([
            event("order-1", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=10),
            event("suspend-1", EventKind.SUSPEND, timestamp=9),
        ])
        outcomes = {entry.event_id: entry.outcome for entry in results}
        self.assertEqual(outcomes["suspend-1"], "applied")
        self.assertEqual(outcomes["order-1"], "blocked")
        self.assertFalse(processor.transactions)

    def test_order_before_later_suspension_is_not_retroactively_blocked(self):
        processor = EventProcessor()
        results = processor.process_batch([
            event("suspend", EventKind.SUSPEND, timestamp=20),
            event("order", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=10),
        ])
        outcomes = {entry.event_id: entry.outcome for entry in results}
        self.assertEqual(outcomes["order"], "applied")
        self.assertEqual(outcomes["suspend"], "applied")
        self.assertTrue(processor.transactions[("ABC", "tx-1")].order_submitted)
        self.assertTrue(processor.instruments["ABC"].suspended)

    def test_equal_timestamp_uses_sequence_before_event_id(self):
        processor = EventProcessor()
        results = processor.process_batch([
            event("order", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=5, sequence=2),
            event("suspend", EventKind.SUSPEND, timestamp=5, sequence=1),
        ])
        outcomes = {entry.event_id: entry.outcome for entry in results}
        self.assertEqual(outcomes["suspend"], "applied")
        self.assertEqual(outcomes["order"], "blocked")

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
        processor.process_batch([event("submit", EventKind.SUBMIT_ORDER, tx="tx-1")])
        result = processor.process_batch([
            event("clear-early", EventKind.CLEARING_CONFIRMED, tx="tx-1", timestamp=2),
        ])[0]
        self.assertEqual(result.outcome, "blocked")
        self.assertFalse(processor.transactions[("ABC", "tx-1")].cleared)

    def test_transaction_progression_and_reachability(self):
        processor = EventProcessor()
        results = processor.process_batch([
            event("submit", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=1),
            event("execute", EventKind.EXECUTION_CONFIRMED, tx="tx-1", timestamp=2),
            event("clear", EventKind.CLEARING_CONFIRMED, tx="tx-1", timestamp=3),
            event("settle", EventKind.SETTLEMENT_CONFIRMED, tx="tx-1", timestamp=4),
        ])
        self.assertTrue(all(entry.outcome == "applied" for entry in results))
        tx = processor.transactions[("ABC", "tx-1")]
        self.assertTrue(all((tx.order_submitted, tx.executed, tx.cleared, tx.settled)))
        self.assertTrue(processor.invariants_hold())

    def test_settlement_cannot_precede_clearing(self):
        processor = EventProcessor()
        processor.process_batch([
            event("submit", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=1),
            event("execute", EventKind.EXECUTION_CONFIRMED, tx="tx-1", timestamp=2),
        ])
        result = processor.process_batch([
            event("settle-early", EventKind.SETTLEMENT_CONFIRMED, tx="tx-1", timestamp=3),
        ])[0]
        self.assertEqual(result.outcome, "blocked")
        self.assertFalse(processor.transactions[("ABC", "tx-1")].settled)

    def test_duplicate_event_id_is_idempotent(self):
        processor = EventProcessor()
        first = event("submit-1", EventKind.SUBMIT_ORDER, tx="tx-1")
        processor.process_batch([first])
        second = processor.process_batch([first])[0]
        self.assertEqual(second.outcome, "ignored")
        self.assertEqual(len(processor.transactions), 1)

    def test_unexpected_failure_rolls_back_entire_batch(self):
        class FailingProcessor(EventProcessor):
            def _apply(self, item):
                if item.event_id == "explode":
                    raise RuntimeError("injected processing failure")
                return super()._apply(item)

        processor = FailingProcessor()
        with self.assertRaisesRegex(RuntimeError, "injected processing failure"):
            processor.process_batch([
                event("suspend-first", EventKind.SUSPEND, timestamp=1),
                event("explode", EventKind.RESUME, timestamp=2),
            ])
        self.assertFalse(processor.instruments)
        self.assertFalse(processor.transactions)
        self.assertFalse(processor.processed_event_ids)
        self.assertFalse(processor.audit_log)
        self.assertFalse(processor.last_event_order)

    def test_validation_failure_is_atomic(self):
        processor = EventProcessor()
        with self.assertRaises(ValueError):
            processor.process_batch([
                event("valid", EventKind.SUSPEND, timestamp=1),
                event("", EventKind.RESUME, timestamp=2),
            ])
        self.assertFalse(processor.instruments)
        self.assertFalse(processor.processed_event_ids)
        self.assertFalse(processor.audit_log)

    def test_duplicate_ids_in_one_batch_rejected_before_processing(self):
        processor = EventProcessor()
        with self.assertRaises(ValueError):
            processor.process_batch([
                event("same", EventKind.SUSPEND),
                event("same", EventKind.SUBMIT_ORDER, tx="tx-1"),
            ])
        self.assertFalse(processor.instruments)
        self.assertFalse(processor.processed_event_ids)

    def test_deterministic_order_independent_of_input_order(self):
        events = [
            event("order", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=2),
            event("suspend", EventKind.SUSPEND, timestamp=1),
        ]
        p1, p2 = EventProcessor(), EventProcessor()
        out1 = [(x.event_id, x.outcome) for x in p1.process_batch(events)]
        out2 = [(x.event_id, x.outcome) for x in p2.process_batch(list(reversed(events)))]
        self.assertEqual(out1, out2)

    def test_late_event_is_rejected_without_rewinding_state(self):
        processor = EventProcessor()
        processor.process_batch([event("suspend-2", EventKind.SUSPEND, timestamp=20)])
        late = processor.process_batch([
            event("resume-1", EventKind.RESUME, timestamp=10),
        ])[0]
        self.assertEqual(late.outcome, "rejected")
        self.assertIn("late event", late.detail)
        self.assertTrue(processor.instruments["ABC"].suspended)

    def test_blocked_order_can_recover_after_resume_with_new_event_id(self):
        processor = EventProcessor()
        processor.process_batch([event("suspend", EventKind.SUSPEND, timestamp=1)])
        blocked = processor.process_batch([
            event("order-attempt-1", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=2),
        ])[0]
        self.assertEqual(blocked.outcome, "blocked")
        processor.process_batch([event("resume", EventKind.RESUME, timestamp=3)])
        retried = processor.process_batch([
            event("order-attempt-2", EventKind.SUBMIT_ORDER, tx="tx-1", timestamp=4),
        ])[0]
        self.assertEqual(retried.outcome, "applied")
        self.assertTrue(processor.transactions[("ABC", "tx-1")].order_submitted)

    def test_nonlisted_instrument_blocks_order(self):
        processor = EventProcessor()
        from market17.event_processor import InstrumentState
        processor.instruments["ABC"] = InstrumentState(listing_status="delisted")
        result = processor.process_batch([
            event("order", EventKind.SUBMIT_ORDER, tx="tx-1"),
        ])[0]
        self.assertEqual(result.outcome, "blocked")

    def test_reachability_invariant_exhaustively_checks_all_flag_combinations(self):
        reachable = []
        for flags in itertools.product((False, True), repeat=4):
            tx = TransactionState(*flags)
            is_reachable = tx.is_reachable()
            if is_reachable:
                reachable.append(flags)
            self.assertEqual(
                is_reachable,
                (not flags[1] or flags[0])
                and (not flags[2] or flags[1])
                and (not flags[3] or flags[2]),
            )
        self.assertEqual(len(reachable), 5)
        self.assertIn((False, False, False, False), reachable)
        self.assertIn((True, True, True, True), reachable)


if __name__ == "__main__":
    unittest.main()
