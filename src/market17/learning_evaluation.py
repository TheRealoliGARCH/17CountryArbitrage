"""Model validation, stress testing, and audit-evidence primitives."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Dict, Mapping, Tuple


@dataclass(frozen=True)
class ValidationReport:
    model_version: str
    dataset_version: str
    validation_window: str
    metrics: Mapping[str, float]
    passed: bool
    reviewer: str
    evidence_reference: str

    def validate(self) -> None:
        if not all((self.model_version, self.dataset_version,
                    self.validation_window, self.reviewer, self.evidence_reference)):
            raise ValueError("model, dataset, window, reviewer, and evidence are required")
        if not self.metrics or any(not key or not isfinite(value)
                                   for key, value in self.metrics.items()):
            raise ValueError("metrics must contain finite named values")


@dataclass(frozen=True)
class StressScenario:
    name: str
    shocks: Mapping[str, float]

    def validate(self) -> None:
        if not self.name or not self.shocks:
            raise ValueError("scenario name and shocks are required")
        if any(not key or not isfinite(value) for key, value in self.shocks.items()):
            raise ValueError("scenario shocks must be finite and named")


@dataclass(frozen=True)
class StressResult:
    scenario_name: str
    portfolio_loss: float
    currency: str
    model_version: str

    def validate(self) -> None:
        if not self.scenario_name or not self.currency or not self.model_version:
            raise ValueError("scenario, currency, and model version are required")
        if not isfinite(self.portfolio_loss):
            raise ValueError("portfolio_loss must be finite")


def approve_model_activation(report: ValidationReport, *, authorized_reviewer: bool) -> bool:
    report.validate()
    return bool(report.passed and authorized_reviewer)
