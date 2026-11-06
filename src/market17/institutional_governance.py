"""Explicit regulatory decisions and instrument-control records."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ControlAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    SUSPEND = "suspend"
    RESUME = "resume"
    DEFAULT = "default"
    DELIST = "delist"
    RELIST = "relist"


@dataclass(frozen=True)
class RegulatoryDecision:
    decision_id: str
    instrument_id: str
    action: ControlAction
    authority: str
    rationale: str
    timestamp: int
    evidence_reference: str
    expires_at: Optional[int] = None

    def validate(self) -> None:
        if not all((self.decision_id, self.instrument_id, self.authority,
                    self.rationale, self.evidence_reference)):
            raise ValueError("decision, instrument, authority, rationale, and evidence are required")
        if self.expires_at is not None and self.expires_at <= self.timestamp:
            raise ValueError("expires_at must be later than decision timestamp")


@dataclass(frozen=True)
class GovernanceResult:
    accepted: bool
    decision_id: str
    reason: str


def record_governance_decision(decision: RegulatoryDecision) -> GovernanceResult:
    """Validate a decision record; authority/permissions require external policy."""
    decision.validate()
    return GovernanceResult(True, decision.decision_id,
                            "decision record structurally valid; authority must be verified externally")
