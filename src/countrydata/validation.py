"""Validation, duplicate classification, and quarantine reporting."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import re
from typing import Iterable

from .panel import Country
from .schema import Observation


QUALITY_STATUSES = {"valid", "missing", "stale", "provisional", "revised", "rejected"}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    field: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    observation: Observation
    issues: tuple[ValidationIssue, ...]

    @property
    def accepted(self) -> bool:
        return not self.issues and self.observation.quality_status != "rejected"

    @property
    def quarantined(self) -> bool:
        return not self.accepted


def validate_observation(
    observation: Observation, panel: dict[str, Country]
) -> ValidationResult:
    issues: list[ValidationIssue] = []

    if observation.country_code not in panel:
        issues.append(ValidationIssue("unknown_country", "Country is not in the canonical panel", "country_code"))
    if not isfinite(observation.value):
        issues.append(ValidationIssue("non_finite_value", "Value must be finite", "value"))
    if not re.fullmatch(r"[A-Z]{3}", observation.currency_code):
        issues.append(ValidationIssue("invalid_currency", "Currency code must be three uppercase letters", "currency_code"))
    for field in ("observation_time", "availability_time", "retrieved_at"):
        timestamp = getattr(observation, field)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            issues.append(ValidationIssue("naive_timestamp", "Timestamp must include an explicit UTC offset", field))
    if observation.quality_status not in QUALITY_STATUSES:
        issues.append(ValidationIssue("invalid_quality_status", "Unknown quality status", "quality_status"))
    if observation.quality_status == "rejected":
        issues.append(ValidationIssue("source_rejected", "Source record is explicitly marked rejected", "quality_status"))
    if observation.availability_time > observation.retrieved_at:
        issues.append(ValidationIssue("future_availability", "Availability time is later than retrieval time", "availability_time"))
    return ValidationResult(observation, tuple(issues))


def validate_batch(
    observations: Iterable[Observation], panel: dict[str, Country]
) -> tuple[list[ValidationResult], list[ValidationResult]]:
    """Validate records and quarantine duplicate keys deterministically.

    Exact repeated records and conflicting records are both quarantined; conflicting
    source records should be retained upstream and reconciled by an explicit policy.
    """
    records = list(observations)
    results = [validate_observation(item, panel) for item in records]
    raw_groups: dict[tuple[str, ...], list[int]] = {}
    project_groups: dict[tuple[str, ...], list[int]] = {}
    for index, item in enumerate(records):
        raw_groups.setdefault(item.raw_key(), []).append(index)
        project_groups.setdefault(item.project_key(), []).append(index)

    duplicate_indices: dict[int, ValidationIssue] = {}
    for key, indices in raw_groups.items():
        if len(indices) > 1:
            for index in indices:
                duplicate_indices[index] = ValidationIssue(
                    "duplicate_raw_key", f"Repeated raw-record key: {key!r}"
                )
    for key, indices in project_groups.items():
        if len(indices) > 1:
            for index in indices:
                duplicate_indices[index] = ValidationIssue(
                    "duplicate_project_key",
                    f"Multiple records share project observation identity: {key!r}",
                )

    accepted: list[ValidationResult] = []
    quarantined: list[ValidationResult] = []
    for index, result in enumerate(results):
        issue = duplicate_indices.get(index)
        if issue:
            result = ValidationResult(result.observation, result.issues + (issue,))
        (accepted if result.accepted else quarantined).append(result)
    return accepted, quarantined
