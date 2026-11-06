"""Canonical country-panel loading and integrity checks."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class Country:
    iso2: str
    country: str
    currency_code: str
    currency: str
    observation_status: str


def load_country_panel(path: str | Path) -> dict[str, Country]:
    """Load the CSV registry, rejecting malformed or non-unique identifiers."""
    panel: dict[str, Country] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"iso2", "country", "currency_code", "currency", "observation_status"}
        if set(reader.fieldnames or ()) != expected:
            raise ValueError("Country panel must contain exactly the documented columns")
        for line_number, row in enumerate(reader, start=2):
            iso2 = (row["iso2"] or "").strip()
            currency_code = (row["currency_code"] or "").strip()
            if not re.fullmatch(r"[A-Z]{2}", iso2):
                raise ValueError(f"Invalid ISO2 code at line {line_number}: {iso2!r}")
            if not re.fullmatch(r"[A-Z]{3}", currency_code):
                raise ValueError(f"Invalid currency code at line {line_number}: {currency_code!r}")
            if iso2 in panel:
                raise ValueError(f"Duplicate country code: {iso2}")
            if any(not (row[key] or "").strip() for key in expected):
                raise ValueError(f"Blank required field at line {line_number}")
            panel[iso2] = Country(
                iso2=iso2,
                country=row["country"].strip(),
                currency_code=currency_code,
                currency=row["currency"].strip(),
                observation_status=row["observation_status"].strip(),
            )
    if len(panel) != 17:
        raise ValueError(f"Expected exactly 17 panel members; found {len(panel)}")
    return panel
