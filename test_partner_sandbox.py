"""Unit tests for the FTS partner sandbox API (Vern)."""

from __future__ import annotations

import unittest

from partner_sandbox import create_test_app


TOKEN = "sandbox-test-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

SAMPLE_AVAIL = {
    "product_id": "FTS-HUR-QUAD-001",
    "date": "2026-10-12",
    "pax": {"adults": 2, "children": 0},
}

SAMPLE_BOOK = {
    **SAMPLE_AVAIL,
    "vern_booking_id": "VERN-100245",
    "pickup_time": "08:00",
    "hotel_name": "Steigenberger Al Dau",
    "customer": {
        "first_name": "Anna",
        "last_name": "Schmidt",
        "email": "anna@example.com",
        "phone": "+491511234567",
    },
}


class PartnerSandboxTests(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app(TOKEN)
        self.client = self.app.test_client()

    def test_health_no_auth(self):
        res = self.client.get("/partner/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertFalse(data["writes_to_airtable"])

    def test_products_requires_auth(self):
        res = self.client.get("/partner/v1/products")
        self.assertEqual(res.status_code, 401)

    def test_products_ok(self):
        res = self.client.get("/partner/v1/products", headers=HEADERS)
        self.assertEqual(res.status_code, 200)
        ids = {p["product_id"] for p in res.get_json()["products"]}
        self.assertIn("FTS-HUR-QUAD-001", ids)

    def test_availability(self):
        res = self.client.post("/partner/v1/availability", json=SAMPLE_AVAIL, headers=HEADERS)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["available"])
        self.assertEqual(data["price"]["adult"], 45.0)

    def test_booking_and_idempotent_replay(self):
        res = self.client.post("/partner/v1/bookings", json=SAMPLE_BOOK, headers=HEADERS)
        self.assertEqual(res.status_code, 201)
        first = res.get_json()
        self.assertEqual(first["fts_confirmation"], "FTS-TEST-88421")
        self.assertTrue(first["sandbox"])

        res2 = self.client.post("/partner/v1/bookings", json=SAMPLE_BOOK, headers=HEADERS)
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.get_json()["idempotent_replay"])

        got = self.client.get("/partner/v1/bookings/VERN-100245", headers=HEADERS)
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.get_json()["fts_confirmation"], "FTS-TEST-88421")

    def test_alias_path(self):
        res = self.client.get("/api/partner/sandbox/health")
        self.assertEqual(res.status_code, 200)

    def test_x_api_key(self):
        res = self.client.get("/partner/v1/products", headers={"X-Api-Key": TOKEN})
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
