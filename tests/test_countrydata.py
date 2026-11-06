import csv
from datetime import date
import math
from pathlib import Path
import tempfile
import unittest

from countrydata.panel import load_country_panel
from countrydata.schema import Observation, ObservationError
from countrydata.validation import validate_batch, validate_observation


ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = ROOT / "config" / "country_panel.csv"


def sample(**overrides):
    data = {
        "country_code": "CH",
        "instrument_id": "CH-GOV-10Y",
        "instrument_type": "sovereign_bond",
        "measure": "mid_yield",
        "observation_time": "2026-11-06T09:00:00+01:00",
        "availability_time": "2026-11-06T09:00:01+01:00",
        "value": -0.25,
        "unit": "percent_per_annum",
        "currency_code": "CHF",
        "source_name": "Example Central Bank",
        "source_series_id": "SERIES-1",
        "retrieved_at": "2026-11-06T09:01:00+01:00",
        "source_vintage": "2026-11-06-release-1",
        "quality_status": "valid",
        "maturity_date": "2036-11-06",
    }
    data.update(overrides)
    return Observation.from_mapping(data)


class TestCountryPanel(unittest.TestCase):
    def test_loads_exactly_17_unique_countries(self):
        panel = load_country_panel(PANEL_PATH)
        self.assertEqual(len(panel), 17)
        self.assertEqual(panel["CH"].currency_code, "CHF")
        self.assertEqual(panel["IN"].currency_code, "INR")

    def test_rejects_duplicate_country_code(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "panel.csv"
            path.write_text(
                "iso2,country,currency_code,currency,observation_status\n"
                "CH,Switzerland,CHF,Swiss franc,panel_member\n"
                "CH,Other,USD,US dollar,panel_member\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_country_panel(path)


class TestObservationSchema(unittest.TestCase):
    def test_parses_valid_record_and_preserves_negative_yield(self):
        item = sample()
        self.assertEqual(item.value, -0.25)
        self.assertEqual(item.maturity_date, date(2036, 11, 6))
        self.assertEqual(item.normalized_times()["observation_time"].isoformat(), "2026-11-06T08:00:00+00:00")

    def test_rejects_naive_timestamp_at_validation(self):
        item = sample(observation_time="2026-11-06T09:00:00")
        result = validate_observation(item, load_country_panel(PANEL_PATH))
        self.assertIn("naive_timestamp", {issue.code for issue in result.issues})

    def test_rejects_unparseable_timestamp(self):
        with self.assertRaises(ObservationError):
            sample(observation_time="not-a-time")

    def test_rejects_boolean_as_numeric_value(self):
        with self.assertRaises(ObservationError):
            sample(value=True)

    def test_non_finite_value_is_quarantined(self):
        item = sample(value=math.inf)
        result = validate_observation(item, load_country_panel(PANEL_PATH))
        self.assertFalse(result.accepted)
        self.assertIn("non_finite_value", {issue.code for issue in result.issues})

    def test_negative_yield_is_not_rejected(self):
        result = validate_observation(sample(value=-1.2), load_country_panel(PANEL_PATH))
        self.assertTrue(result.accepted)

    def test_unknown_country_is_quarantined(self):
        result = validate_observation(sample(country_code="ZZ"), load_country_panel(PANEL_PATH))
        self.assertIn("unknown_country", {issue.code for issue in result.issues})

    def test_future_availability_is_quarantined(self):
        item = sample(availability_time="2026-11-06T10:00:00+01:00")
        result = validate_observation(item, load_country_panel(PANEL_PATH))
        self.assertIn("future_availability", {issue.code for issue in result.issues})

    def test_explicitly_rejected_quality_status_is_quarantined(self):
        result = validate_observation(sample(quality_status="rejected"), load_country_panel(PANEL_PATH))
        self.assertFalse(result.accepted)


class TestBatchAndDuplicates(unittest.TestCase):
    def test_valid_batch_is_accepted(self):
        accepted, quarantined = validate_batch([sample(), sample(instrument_id="CH-GOV-5Y")], load_country_panel(PANEL_PATH))
        self.assertEqual(len(accepted), 2)
        self.assertEqual(quarantined, [])

    def test_exact_duplicate_raw_key_is_quarantined(self):
        accepted, quarantined = validate_batch([sample(), sample()], load_country_panel(PANEL_PATH))
        self.assertEqual(accepted, [])
        self.assertEqual(len(quarantined), 2)
        self.assertIn("duplicate_raw_key", {issue.code for result in quarantined for issue in result.issues})

    def test_cross_source_conflict_on_project_key_is_quarantined(self):
        first = sample()
        second = sample(source_name="Another Publisher", source_series_id="SERIES-OTHER", value=0.1)
        accepted, quarantined = validate_batch([first, second], load_country_panel(PANEL_PATH))
        self.assertEqual(accepted, [])
        self.assertEqual(len(quarantined), 2)
        self.assertIn("duplicate_project_key", {issue.code for result in quarantined for issue in result.issues})

    def test_different_source_vintages_are_not_duplicates(self):
        accepted, quarantined = validate_batch(
            [sample(), sample(source_vintage="2026-11-06-release-2")],
            load_country_panel(PANEL_PATH),
        )
        self.assertEqual(len(accepted), 2)
        self.assertEqual(quarantined, [])


if __name__ == "__main__":
    unittest.main()
