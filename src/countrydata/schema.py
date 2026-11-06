"""Typed representation of one source-vintage observation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


class ObservationError(ValueError):
    """Raised when an input mapping cannot form an observation."""


def _required_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ObservationError(f"{key} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class Observation:
    country_code: str
    instrument_id: str
    instrument_type: str
    measure: str
    observation_time: datetime
    availability_time: datetime
    value: float
    unit: str
    currency_code: str
    source_name: str
    source_series_id: str
    retrieved_at: datetime
    source_vintage: str
    quality_status: str
    maturity_date: date | None = None
    tenor: str | None = None
    day_count: str | None = None
    compounding: str | None = None
    notes: str = ""

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Observation":
        """Parse ISO-8601 timestamps without discarding their UTC offsets."""
        required = (
            "country_code", "instrument_id", "instrument_type", "measure",
            "unit", "currency_code", "source_name", "source_series_id",
            "source_vintage", "quality_status",
        )
        values = {key: _required_text(data, key) for key in required}
        timestamps = {}
        for key in ("observation_time", "availability_time", "retrieved_at"):
            raw = data.get(key)
            if not isinstance(raw, str) or not raw.strip():
                raise ObservationError(f"{key} must be an ISO-8601 timestamp")
            try:
                parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise ObservationError(f"Invalid {key}: {raw!r}") from exc
            timestamps[key] = parsed
        raw_value = data.get("value")
        if isinstance(raw_value, bool):
            raise ObservationError("value must be numeric, not boolean")
        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise ObservationError("value must be numeric") from exc
        maturity = data.get("maturity_date")
        if maturity in (None, ""):
            maturity_date = None
        elif isinstance(maturity, date) and not isinstance(maturity, datetime):
            maturity_date = maturity
        elif isinstance(maturity, str):
            try:
                maturity_date = date.fromisoformat(maturity)
            except ValueError as exc:
                raise ObservationError("maturity_date must be an ISO date") from exc
        else:
            raise ObservationError("maturity_date must be an ISO date or null")
        optional = {}
        for key in ("tenor", "day_count", "compounding"):
            value = data.get(key)
            optional[key] = value.strip() if isinstance(value, str) and value.strip() else None
        notes = data.get("notes", "")
        if not isinstance(notes, str):
            raise ObservationError("notes must be a string")
        return cls(
            **values, **timestamps, value=numeric_value,
            maturity_date=maturity_date, **optional, notes=notes,
        )

    def normalized_times(self) -> dict[str, datetime]:
        """Return UTC-normalized timestamps; original offset-aware values remain intact."""
        from datetime import timezone
        return {
            key: getattr(self, key).astimezone(timezone.utc)
            for key in ("observation_time", "availability_time", "retrieved_at")
        }

    def raw_key(self) -> tuple[str, ...]:
        return (
            self.source_name, self.source_series_id, self.instrument_id,
            self.measure, self.observation_time.isoformat(), self.source_vintage,
        )

    def project_key(self) -> tuple[str, ...]:
        return (
            self.country_code, self.instrument_id, self.measure,
            self.observation_time.isoformat(), self.source_vintage,
        )
