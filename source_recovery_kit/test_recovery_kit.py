#!/usr/bin/env python3
"""CPU-only tests for the independent source-recovery tooling."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from build_station_source_queue import generate
from compare_gee_export import compare_exports
from generate_gee_script import build_points, render


HERE = Path(__file__).resolve().parent


def write_csv(path: Path, rows: list[dict]):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class RecoveryTests(unittest.TestCase):
    def test_gee_generation_has_all_points_and_units(self):
        original = build_points(HERE / "station_points_author_draft.csv")
        self.assertEqual(36, len(original))
        with tempfile.TemporaryDirectory() as d:
            js = Path(d) / "generated.js"
            summary = render(HERE / "station_points_author_draft.csv",
                             HERE / "gee_era5land_daily_template.js", js)
            source = js.read_text(encoding="utf-8")
            self.assertEqual(36, summary["station_count"])
            self.assertNotIn("__POINTS_JS__", source)
            self.assertIn("ECMWF/ERA5_LAND/DAILY_AGGR", source)
            self.assertIn("rain_m", source)
            self.assertIn("date_utc", source)
            self.assertIn("author_draft_unverified_historical", source)

    def test_historical_coordinate_queue_not_certified(self):
        with tempfile.TemporaryDirectory() as d:
            destination = Path(d)
            summary = generate(HERE / "station_metadata_author_draft.csv",
                               HERE / "bamis_station_coordinates_public_2026.csv",
                               destination / "queue.csv", destination / "queue.json")
            self.assertEqual(36, summary["author_stations"])
            with (destination / "queue.csv").open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertTrue(all(r["historical_2000_2023_site_moves_verified"] == "NO" for r in rows))
            self.assertGreater(sum(r["verification_priority"].startswith("P0") for r in rows), 0)

    def test_export_comparison_and_unit_conversions(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            reference = dest / "reference.csv"
            export = dest / "gee.csv"
            write_csv(reference, [{
                "point_id": "S01", "date": "2023-09-05", "era5_source": "native",
                "t2m_mean": "25", "prcp": "12", "ssrd": "18",
                "sp": "100", "pet_era5": "4", "u10": "1",
            }])
            write_csv(export, [{
                "point_id": "S01", "date_utc": "2023-09-05",
                "t2m_C": "25", "rain_m": "0.012", "rain_mm_raw": "12", "rain_mm_clipped": "12",
                "ssrd_MJ_m2_day": "18", "sp_kPa": "100",
                "pet_evap_positive_mm": "4", "u10_ms": "1",
            }])
            result = compare_exports(reference, [export], dest / "result")
            self.assertEqual(1, result["native_days_compared"])
            self.assertEqual(0, result["total_field_discrepancies"])
            self.assertEqual(0, result["new_export_stats"].get("unit_conversion_inconsistent_rows", 0))
            self.assertEqual(6, len(result["per_field"]))

            write_csv(export, [{
                "point_id": "S01", "date_utc": "2023-09-05", "t2m_C": "25",
                "rain_m": "0.020", "rain_mm_raw": "20", "rain_mm_clipped": "20",
                "ssrd_MJ_m2_day": "18", "sp_kPa": "100",
                "pet_evap_positive_mm": "4", "u10_ms": "1",
            }])
            mismatched = compare_exports(reference, [export], dest / "bad")
            self.assertEqual(1, mismatched["total_field_discrepancies"])
            self.assertEqual(1, json.loads((dest / "bad/gee_comparison_summary.json").read_text())
                             ["per_station"]["S01"]["field_failures"])

    def test_negative_raw_rain_clipping_matches_original(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d)
            reference, export = dest / "reference.csv", dest / "export.csv"
            write_csv(reference, [{
                "point_id": "S01", "date": "2019-01-01", "era5_source": "native", "prcp": "0",
            }])
            write_csv(export, [{
                "point_id": "S01", "date_utc": "2019-01-01",
                "rain_m": "-0.00000002", "rain_mm_raw": "-0.00002", "rain_mm_clipped": "0",
            }])
            result = compare_exports(reference, [export], dest / "out")
            self.assertEqual(0, result["total_field_discrepancies"])
            self.assertEqual(1, result["new_export_stats"]["negative_native_precipitation_rows"])


if __name__ == "__main__":
    unittest.main()
