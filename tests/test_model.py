import unittest

from market17.model import (
    ArbitrageContext,
    DelistingContext,
    OHLC,
    State,
    SUBSYSTEM_STATES,
    TRANSITIONS,
    may_activate_model_revision,
    may_settle,
    may_submit_ordinary_order,
    transition_permitted,
)


class TestStateArchitecture(unittest.TestCase):
    def test_exactly_17_named_states(self):
        self.assertEqual(len(State), 17)

    def test_subsystems_partition_all_named_states(self):
        assigned = []
        for states in SUBSYSTEM_STATES.values():
            assigned.extend(states)
        self.assertEqual(len(assigned), 17)
        self.assertEqual(set(assigned), set(State))
        self.assertEqual(len(set(assigned)), len(assigned))

    def test_every_state_has_transition_entry(self):
        self.assertEqual(set(TRANSITIONS), set(State))

    def test_transition_lookup_distinguishes_adjacency(self):
        self.assertTrue(transition_permitted(State.ARBITRAGE, State.ORDER_EXECUTION))
        self.assertFalse(transition_permitted(State.ARBITRAGE, State.DELISTING))


class TestOHLC(unittest.TestCase):
    def test_valid_ohlc(self):
        self.assertTrue(OHLC(open=10, high=15, low=8, close=12).is_valid())

    def test_rejects_low_above_open(self):
        self.assertFalse(OHLC(open=10, high=15, low=11, close=12).is_valid())

    def test_rejects_high_below_close(self):
        self.assertFalse(OHLC(open=10, high=11, low=8, close=12).is_valid())

    def test_rejects_non_finite_values(self):
        self.assertFalse(OHLC(open=10, high=float("inf"), low=8, close=9).is_valid())


class TestArbitrageGuard(unittest.TestCase):
    def test_all_conditions_allow_candidate_execution(self):
        context = ArbitrageContext(
            data_valid=True, net_profit=2.0, minimum_profit=0.5,
            sufficient_liquidity=True, risk_policy_passed=True,
        )
        self.assertTrue(context.may_execute())

    def test_invalid_data_blocks_execution(self):
        context = ArbitrageContext(
            data_valid=False, net_profit=2.0, sufficient_liquidity=True,
            risk_policy_passed=True,
        )
        self.assertFalse(context.may_execute())

    def test_nonpositive_margin_under_threshold_blocks_execution(self):
        context = ArbitrageContext(
            data_valid=True, net_profit=0.0, minimum_profit=0.0,
            sufficient_liquidity=True, risk_policy_passed=True,
        )
        self.assertFalse(context.may_execute())

    def test_insufficient_liquidity_blocks_execution(self):
        context = ArbitrageContext(
            data_valid=True, net_profit=2.0, sufficient_liquidity=False,
            risk_policy_passed=True,
        )
        self.assertFalse(context.may_execute())


class TestGovernanceAndIntegrityGuards(unittest.TestCase):
    def test_negative_premium_alone_does_not_authorize_delisting(self):
        context = DelistingContext(
            negative_premium_signal=True,
            risk_assessment_complete=False,
            delisting_criteria_satisfied=False,
            authorization_obtained=False,
        )
        self.assertFalse(context.may_delist())

    def test_delisting_requires_all_conditions(self):
        context = DelistingContext(
            negative_premium_signal=True,
            risk_assessment_complete=True,
            delisting_criteria_satisfied=True,
            authorization_obtained=True,
        )
        self.assertTrue(context.may_delist())

    def test_settlement_requires_clearing(self):
        self.assertFalse(may_settle(False))
        self.assertTrue(may_settle(True))

    def test_suspension_blocks_ordinary_new_order(self):
        self.assertFalse(may_submit_ordinary_order(True, True))
        self.assertTrue(may_submit_ordinary_order(False, True))

    def test_model_revision_requires_tests_and_approval(self):
        self.assertFalse(may_activate_model_revision(True, False))
        self.assertFalse(may_activate_model_revision(False, True))
        self.assertTrue(may_activate_model_revision(True, True))


if __name__ == "__main__":
    unittest.main()
