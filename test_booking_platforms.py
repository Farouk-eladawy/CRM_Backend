"""Tests for dashboard booking-platform settings helpers."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest import mock


class BookingPlatformsHelperTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.data_dir = self._tmp.name

    def _patch_paths(self):
        def fake_get_data_path(filename):
            return os.path.join(self.data_dir, filename)
        return mock.patch.multiple(
            "booking_platforms",
            get_data_path=fake_get_data_path,
            SCRIPT_DIR=self.data_dir,
        )

    def test_defaults_include_viator_and_other_otas(self):
        import booking_platforms as bp
        with self._patch_paths():
            settings = bp.get_all_platform_settings()
        self.assertIn("viator", settings)
        self.assertIn("getyourguide", settings)
        self.assertIn("headout", settings)
        self.assertIn("tiqets", settings)
        self.assertTrue(settings["viator"]["enabled"])
        self.assertEqual(settings["viator"]["ingest_mode"], "api")
        self.assertEqual(settings["getyourguide"]["ingest_mode"], "api")
        self.assertEqual(settings["getyourguide"]["currency"], "EUR")
        self.assertEqual(settings["getyourguide"]["supplier_id"], "S707722")

    def test_save_keeps_existing_secret_when_masked(self):
        import booking_platforms as bp
        with self._patch_paths():
            bp.save_platform_settings("viator", {"api_key": "real-secret-key-9999", "enabled": True})
            bp.save_platform_settings("viator", {"api_key": "••••9999", "enabled": True, "environment": "production"})
            stored = bp.get_all_platform_settings()["viator"]
        self.assertEqual(stored["api_key"], "real-secret-key-9999")
        self.assertEqual(stored["environment"], "production")
        public = bp._public_platform(stored)
        self.assertTrue(public["api_key"].startswith("••••"))
        self.assertTrue(public["api_key_configured"])

    def test_product_live_flag_roundtrip(self):
        import booking_platforms as bp
        catalog = {
            "currency": "USD",
            "products": [{
                "supplier_product_code": "LUXOR-HRG",
                "supplier_product_name": "Luxor",
                "live": True,
                "api_connected": False,
                "daily_capacity": 15,
                "cutoff_hours": 12,
            }],
        }
        with self._patch_paths():
            path = os.path.join(self.data_dir, "viator_products.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(catalog, handle)
            saved = bp.save_viator_products([{
                "supplier_product_code": "LUXOR-HRG",
                "live": False,
                "api_connected": True,
                "daily_capacity": 9,
                "pickup_offered": True,
                "start_times_mode": True,
                "options": [{
                    "supplier_option_code": "TG1",
                    "supplier_option_name": "With lunch",
                    "departure_time": "04:00:00",
                    "adult_net": 80,
                }],
                "age_bands": {"Adult": {"enabled": True, "min_age": 13, "max_age": 99}},
            }])
        row = saved["products"][0]
        self.assertFalse(row["live"])
        self.assertTrue(row["api_connected"])
        self.assertEqual(row["daily_capacity"], 9)
        self.assertEqual(row["cutoff_hours"], 12)
        self.assertTrue(row["pickup_offered"])
        self.assertTrue(row["start_times_mode"])
        self.assertEqual(row["options"][0]["supplier_option_code"], "TG1")
        self.assertEqual(row["age_bands"]["Adult"]["min_age"], 13)

    def test_gyg_product_live_flag_roundtrip(self):
        import booking_platforms as bp
        catalog = {
            "supplier_id": "S707722",
            "currency": "EUR",
            "products": [{
                "product_id": "SERA",
                "gyg_tour_id": "1441222",
                "product_title": "Serabit",
                "live": True,
                "api_connected": False,
                "daily_capacity": 100,
                "cutoff_hours": 5,
                "schedules_loaded": True,
            }],
        }
        with self._patch_paths():
            path = os.path.join(self.data_dir, "gyg_products.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(catalog, handle)
            saved = bp.save_gyg_products([{
                "product_id": "SERA",
                "live": False,
                "api_connected": True,
                "daily_capacity": 40,
                "cutoff_hours": 6,
                "departure_times": ["07:00:00"],
                "categories": {
                    "ADULT": {"enabled": True, "retail_minor": 19900, "age_from": 12, "age_to": 99},
                },
                "product_title": "SHOULD_NOT_SAVE",
            }])
        row = saved["products"][0]
        self.assertFalse(row["live"])
        self.assertTrue(row["api_connected"])
        self.assertEqual(row["daily_capacity"], 40)
        self.assertEqual(row["cutoff_hours"], 6)
        self.assertEqual(row["cutoff_seconds"], 21600)
        self.assertEqual(row["departure_times"], ["07:00:00"])
        self.assertEqual(row["categories"]["ADULT"]["retail_minor"], 19900)
        # Marketing content must not be overwritten from the UI save path.
        self.assertEqual(row["product_title"], "Serabit")
        self.assertTrue(row["schedules_loaded"])
        self.assertEqual(row["gyg_tour_id"], "1441222")


if __name__ == "__main__":
    unittest.main()
