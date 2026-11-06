import unittest

from market17.price_formation import (
    AuctionResult, CircuitBreaker, Order, OrderBook, Side, call_auction,
)
from market17.market_intelligence import (
    MarketObservation, net_arbitrage_candidate, robust_price_anomalies,
)
from market17.transaction_operations import (
    CollateralPosition, MarginRequirement, assess_collateral,
    may_settle_after_clearing,
)
from market17.institutional_governance import (
    ControlAction, RegulatoryDecision, record_governance_decision,
)
from market17.learning_evaluation import (
    StressScenario, StressResult, ValidationReport, approve_model_activation,
)


def order(order_id, side, price, quantity=10):
    return Order(order_id, "BOND-1", "P-"+order_id, side, price, quantity, 1)


class TestPriceFormation(unittest.TestCase):
    def test_order_book_best_bid_ask(self):
        book = OrderBook("BOND-1")
        book.add(order("b1", Side.BUY, 99))
        book.add(order("b2", Side.BUY, 100))
        book.add(order("a1", Side.SELL, 101))
        self.assertEqual(book.best_bid_ask(), (100, 101))

    def test_book_rejects_duplicate_and_wrong_instrument(self):
        book = OrderBook("BOND-1")
        row = order("b1", Side.BUY, 99)
        book.add(row)
        with self.assertRaises(ValueError):
            book.add(row)
        with self.assertRaises(ValueError):
            book.add(Order("x", "OTHER", "p", Side.BUY, 1, 1, 1))

    def test_call_auction_maximizes_executable_volume(self):
        result = call_auction([
            order("b1", Side.BUY, 102, 10),
            order("b2", Side.BUY, 101, 5),
            order("a1", Side.SELL, 99, 8),
            order("a2", Side.SELL, 100, 7),
        ])
        self.assertEqual(result.price, 101)
        self.assertEqual(result.quantity, 15)

    def test_circuit_breaker_requires_authorized_reset(self):
        breaker = CircuitBreaker(0.1)
        self.assertTrue(breaker.observe(100, 112))
        with self.assertRaises(PermissionError):
            breaker.reset(authorized=False)
        breaker.reset(authorized=True)
        self.assertFalse(breaker.halted)


class TestMarketIntelligence(unittest.TestCase):
    def test_robust_outlier_alert_is_review_only(self):
        rows = [
            MarketObservation("BOND", i, price, 10, "feed")
            for i, price in enumerate([100, 100.1, 99.9, 100.05, 130])
        ]
        alerts = robust_price_anomalies(rows, z_threshold=3)
        self.assertEqual(len(alerts), 1)
        self.assertTrue(alerts[0].requires_human_review)

    def test_net_edge_must_exceed_all_costs(self):
        self.assertTrue(net_arbitrage_candidate(
            10, spread_cost=1, fees=1, funding_cost=1, hedge_cost=1,
            market_impact=1, settlement_cost=1,
        ))
        self.assertFalse(net_arbitrage_candidate(
            6, spread_cost=1, fees=1, funding_cost=1, hedge_cost=1,
            market_impact=1, settlement_cost=1,
        ))


class TestTransactionOperations(unittest.TestCase):
    def test_collateral_haircut_and_shortfall(self):
        position = CollateralPosition("P1", "USD", 100, 0.2)
        result = assess_collateral("TX1", 85, {"gold": position})
        self.assertFalse(result.accepted)
        self.assertEqual(result.eligible_collateral, 80)
        self.assertEqual(result.shortfall, 5)

    def test_margin_is_nonnegative_and_currency_tagged(self):
        self.assertEqual(MarginRequirement(10, 2, "USD").total, 12)
        with self.assertRaises(ValueError):
            MarginRequirement(-1, 0, "USD").total

    def test_settlement_requires_clearing_and_instruction(self):
        self.assertFalse(may_settle_after_clearing(False, True))
        self.assertFalse(may_settle_after_clearing(True, False))
        self.assertTrue(may_settle_after_clearing(True, True))


class TestInstitutionalGovernance(unittest.TestCase):
    def test_decision_requires_authority_rationale_and_evidence(self):
        decision = RegulatoryDecision(
            "D1", "BOND-1", ControlAction.SUSPEND, "regulator",
            "risk trigger", 10, "audit://evidence/1",
        )
        result = record_governance_decision(decision)
        self.assertTrue(result.accepted)
        with self.assertRaises(ValueError):
            record_governance_decision(RegulatoryDecision(
                "", "BOND-1", ControlAction.SUSPEND, "", "", 10, "",
            ))


class TestLearningEvaluation(unittest.TestCase):
    def test_model_activation_requires_passed_report_and_authorized_reviewer(self):
        report = ValidationReport(
            "v2", "data-1", "2025Q1", {"sharpe": 1.2, "max_drawdown": 0.1},
            True, "reviewer-1", "audit://validation/1",
        )
        self.assertFalse(approve_model_activation(report, authorized_reviewer=False))
        self.assertTrue(approve_model_activation(report, authorized_reviewer=True))

    def test_stress_scenario_and_result_validation(self):
        StressScenario("rates-up", {"yield_curve_bp": 200}).validate()
        StressResult("rates-up", 1000, "USD", "v2").validate()


if __name__ == "__main__":
    unittest.main()
