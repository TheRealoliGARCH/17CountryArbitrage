"""Surveillance and anomaly-detection primitives.

Signals are alerts for review, not findings of misconduct or trade commands.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import median
from typing import Iterable, Tuple


@dataclass(frozen=True)
class MarketObservation:
    instrument_id: str
    timestamp: int
    price: float
    volume: float
    source_id: str

    def validate(self) -> None:
        if not self.instrument_id or not self.source_id:
            raise ValueError("instrument_id and source_id are required")
        if not isfinite(self.price) or self.price <= 0:
            raise ValueError("price must be finite and positive")
        if not isfinite(self.volume) or self.volume < 0:
            raise ValueError("volume must be finite and nonnegative")


@dataclass(frozen=True)
class SurveillanceAlert:
    instrument_id: str
    timestamp: int
    alert_type: str
    severity: str
    metric: float
    threshold: float
    source_id: str
    requires_human_review: bool = True


def robust_price_anomalies(
    observations: Iterable[MarketObservation],
    *,
    z_threshold: float = 6.0,
) -> Tuple[SurveillanceAlert, ...]:
    """Flag robust cross-sectional price outliers using median/MAD.

    This simple batch diagnostic assumes observations are comparable by
    instrument. It is not a market-manipulation classifier.
    """
    rows = tuple(observations)
    for row in rows:
        row.validate()
    if not isfinite(z_threshold) or z_threshold <= 0:
        raise ValueError("z_threshold must be finite and positive")
    by_instrument = {}
    for row in rows:
        by_instrument.setdefault(row.instrument_id, []).append(row)
    alerts = []
    for instrument_id, series in by_instrument.items():
        prices = [row.price for row in series]
        center = median(prices)
        mad = median([abs(value - center) for value in prices])
        if mad == 0:
            continue
        scale = 1.4826 * mad
        for row in series:
            score = abs(row.price - center) / scale
            if score >= z_threshold:
                alerts.append(SurveillanceAlert(
                    instrument_id, row.timestamp, "robust_price_outlier",
                    "review", score, z_threshold, row.source_id,
                ))
    return tuple(sorted(alerts, key=lambda a: (a.timestamp, a.instrument_id, a.source_id)))


def net_arbitrage_candidate(
    gross_edge: float,
    *,
    spread_cost: float,
    fees: float,
    funding_cost: float,
    hedge_cost: float,
    market_impact: float,
    settlement_cost: float,
    required_buffer: float = 0.0,
) -> bool:
    """Return a candidate flag only when edge exceeds enumerated costs.

    All inputs must use the same currency, unit, and horizon. This is not
    sufficient for execution: liquidity, limits, counterparty and legal
    eligibility must be checked separately.
    """
    values = (gross_edge, spread_cost, fees, funding_cost, hedge_cost,
              market_impact, settlement_cost, required_buffer)
    if not all(isfinite(value) for value in values):
        raise ValueError("all monetary inputs must be finite")
    if any(value < 0 for value in values[1:]):
        raise ValueError("costs and required_buffer must be nonnegative")
    total_cost = sum(values[1:])
    return gross_edge > total_cost
