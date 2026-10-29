import unittest

from market17.state_explorer import (
    Action, ListingStatus, MarketState, ModelStatus, explore,
    invariant_violations, successors,
)


class TestStateExplorer(unittest.TestCase):
    def test_default_model_has_no_invariant_violations(self):
        result = explore(max_depth=8)
        self.assertGreater(len(result.states), 1)
        self.assertTrue(result.transitions)
        self.assertEqual(result.counterexamples, ())

    def test_transaction_progression_is_guarded(self):
        state = MarketState(transaction_stage=1)
        actions = {action for action, _ in successors(state)}
        self.assertIn(Action.EXECUTE, actions)
        self.assertNotIn(Action.CLEAR, actions)
        self.assertNotIn(Action.SETTLE, actions)

    def test_suspended_instrument_cannot_submit_order(self):
        state = MarketState(listing=ListingStatus.SUSPENDED)
        actions = {action for action, _ in successors(state)}
        self.assertNotIn(Action.SUBMIT_ORDER, actions)
        self.assertIn(Action.RESUME, actions)
        self.assertIn(Action.DELIST, actions)

    def test_delisted_instrument_requires_eligibility_and_approval_to_relist(self):
        state = MarketState(listing=ListingStatus.DELISTED)
        actions = {action for action, _ in successors(state)}
        self.assertNotIn(Action.RELIST, actions)
        eligible = next(target for action, target in successors(state)
                        if action is Action.MARK_RELIST_ELIGIBLE)
        actions_after_eligibility = {action for action, _ in successors(eligible)}
        self.assertNotIn(Action.RELIST, actions_after_eligibility)
        approved = next(target for action, target in successors(eligible)
                        if action is Action.APPROVE_RELISTING)
        self.assertIn(Action.RELIST, {action for action, _ in successors(approved)})

    def test_model_activation_requires_testing_and_approval(self):
        state = MarketState(model_status=ModelStatus.REVISING)
        self.assertNotIn(Action.ACTIVATE_MODEL_REVISION,
                         {action for action, _ in successors(state)})
        tested = next(target for action, target in successors(state)
                      if action is Action.TEST_MODEL_REVISION)
        self.assertNotIn(Action.ACTIVATE_MODEL_REVISION,
                         {action for action, _ in successors(tested)})
        approved = next(target for action, target in successors(tested)
                        if action is Action.APPROVE_MODEL_REVISION)
        self.assertIn(Action.ACTIVATE_MODEL_REVISION,
                      {action for action, _ in successors(approved)})

    def test_counterexample_contains_trace_for_injected_bad_state(self):
        bad = MarketState(transaction_stage=5)
        result = explore(
            initial=bad,
            max_depth=0,
            invariant=lambda state: not invariant_violations(state),
        )
        self.assertEqual(len(result.counterexamples), 1)
        self.assertEqual(result.counterexamples[0].trace, ())
        self.assertIn("transaction stage", invariant_violations(bad)[0])

    def test_depth_is_validated(self):
        with self.assertRaises(ValueError):
            explore(max_depth=-1)


if __name__ == "__main__":
    unittest.main()
