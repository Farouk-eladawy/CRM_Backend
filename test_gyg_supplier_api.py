"""Unit tests for the GetYourGuide Supplier-side API."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from urllib.parse import quote

from gyg_supplier_api import GYGStore, create_test_app, _basic_auth_header


TEST_USER = "gyg-test-user"
TEST_PASS = "gyg-test-pass"
SUPPLIER_ID = "fts-travels"
PRODUCT_ID = "LUXOR-HRG"
SLOT_DT = "2026-12-10T03:00:00+02:00"


def _cfg(**extra):
    cfg = {
        "enabled": True,
        "basic_user": TEST_USER,
        "basic_pass": TEST_PASS,
        "supplier_id": SUPPLIER_ID,
        "environment": "sandbox",
        "async_airtable": False,
        "ip_allowlist": [],
        "products_file": "gyg_products.json",
    }
    cfg.update(extra)
    return cfg


SAMPLE_RESERVE = {
    "data": {
        "bookingItems": [
            {"category": "ADULT", "count": 2},
            {"category": "CHILD", "count": 1},
        ],
        "dateTime": SLOT_DT,
        "productId": PRODUCT_ID,
        "gygBookingReference": "GYGTEST001",
    }
}

SAMPLE_BOOK = {
    "data": {
        "bookingItems": [
            {"category": "ADULT", "count": 2, "retailPrice": 11000},
            {"category": "CHILD", "count": 1, "retailPrice": 8500},
        ],
        "dateTime": SLOT_DT,
        "currency": "EUR",
        "gygBookingReference": "GYGTEST001",
        "productId": PRODUCT_ID,
        "reservationReference": "RES-PLACEHOLDER",
        "travelers": [
            {
                "email": "john@example.com",
                "firstName": "John",
                "lastName": "Smith",
                "phoneNumber": "+49 030 1231231",
            }
        ],
        "comment": "Hotel Sunrise Azalea Aqua park",
    }
}


class GYGSupplierApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.app = create_test_app(config_override=_cfg(), db_path=self._tmp.name)
        self.client = self.app.test_client()
        self.headers = _basic_auth_header(TEST_USER, TEST_PASS)

    def tearDown(self):
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_health_does_not_require_auth(self):
        resp = self.client.get("/gyg/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["status"], "ok")
        self.assertGreaterEqual(body["live_products"], 1)

    def test_invalid_basic_auth_is_rejected(self):
        resp = self.client.get(
            self._availability_url("2026-12-01T00:00:00+02:00", "2026-12-01T23:59:59+02:00"),
            headers=_basic_auth_header("wrong", "creds"),
        )
        self.assertEqual(resp.status_code, 401)

    def _availability_url(self, from_dt: str, to_dt: str, product_id: str = PRODUCT_ID) -> str:
        return (
            f"/gyg/1/get-availabilities?productId={quote(product_id)}"
            f"&fromDateTime={quote(from_dt, safe='')}&toDateTime={quote(to_dt, safe='')}"
        )

    def test_products_list_returns_live_products(self):
        resp = self.client.get(f"/gyg/1/suppliers/{SUPPLIER_ID}/products", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        products = resp.get_json()["data"]["products"]
        ids = [p["productId"] for p in products]
        self.assertIn(PRODUCT_ID, ids)

    def test_availability_returns_slots_with_prices(self):
        resp = self.client.get(
            self._availability_url("2026-12-10T00:00:00+02:00", "2026-12-10T23:59:59+02:00"),
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        slots = resp.get_json()["data"]["availabilities"]
        self.assertTrue(slots)
        self.assertIn("vacancies", slots[0])
        self.assertIn("pricesByCategory", slots[0])

    def test_reserve_book_cancel_flow(self):
        reserve = self.client.post("/gyg/1/reserve", headers=self.headers, json=SAMPLE_RESERVE)
        self.assertEqual(reserve.status_code, 200)
        reserve_body = reserve.get_json()["data"]
        self.assertIn("reservationReference", reserve_body)
        self.assertIn("reservationExpiration", reserve_body)

        book_payload = json.loads(json.dumps(SAMPLE_BOOK))
        book_payload["data"]["reservationReference"] = reserve_body["reservationReference"]
        book = self.client.post("/gyg/1/book", headers=self.headers, json=book_payload)
        self.assertEqual(book.status_code, 200)
        book_body = book.get_json()["data"]
        self.assertEqual(book_body["bookingReference"], "FTS-GYGTEST001")
        self.assertTrue(book_body.get("tickets"))

        store = GYGStore(db_path=self._tmp.name)
        row = store.get_booking_by_gyg("GYGTEST001")
        self.assertEqual(row["lead_name"], "John Smith")
        self.assertEqual(row["adults"], 2)
        self.assertEqual(row["children"], 1)
        self.assertEqual(row["pickup_point"], "Hotel Sunrise Azalea Aqua park")
        self.assertEqual(row["phone"], "+490301231231")

        duplicate = self.client.post("/gyg/1/book", headers=self.headers, json=book_payload)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.get_json()["data"]["bookingReference"], "FTS-GYGTEST001")
        with store._connect() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM bookings WHERE gyg_booking_reference = ?",
                ("GYGTEST001",),
            ).fetchone()[0]
        self.assertEqual(count, 1)

        cancel = self.client.post(
            "/gyg/1/cancel-booking",
            headers=self.headers,
            json={
                "data": {
                    "bookingReference": "FTS-GYGTEST001",
                    "gygBookingReference": "GYGTEST001",
                    "productId": PRODUCT_ID,
                }
            },
        )
        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(store.get_booking_by_gyg("GYGTEST001")["status"], "CANCELLED")

    def test_reserve_blocks_when_capacity_full(self):
        products_path = self._tmp.name + ".products.json"
        with open(products_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "currency": "EUR",
                    "supplier_id": SUPPLIER_ID,
                    "supplier_name": "FTS Travels",
                    "products": [{
                        "product_id": "TINY",
                        "product_title": "Tiny test tour",
                        "live": True,
                        "daily_capacity": 2,
                        "cutoff_hours": 0,
                        "departure_times": ["09:00:00"],
                        "categories": {
                            "ADULT": {"enabled": True, "retail_minor": 1000},
                        },
                    }],
                },
                handle,
            )
        app = create_test_app(config_override=_cfg(products_file=products_path), db_path=self._tmp.name + ".tiny.db")
        client = app.test_client()
        headers = self.headers
        book_payload = {
            "data": {
                "bookingItems": [{"category": "ADULT", "count": 2, "retailPrice": 1000}],
                "dateTime": "2026-12-11T09:00:00+02:00",
                "currency": "EUR",
                "gygBookingReference": "GYGTINY001",
                "productId": "TINY",
                "travelers": [{"firstName": "A", "lastName": "B", "email": "a@b.com"}],
            }
        }
        self.assertEqual(client.post("/gyg/1/book", headers=headers, json=book_payload).status_code, 200)

        reserve = client.post(
            "/gyg/1/reserve",
            headers=headers,
            json={
                "data": {
                    "bookingItems": [{"category": "ADULT", "count": 1}],
                    "dateTime": "2026-12-11T09:00:00+02:00",
                    "productId": "TINY",
                    "gygBookingReference": "GYGTINY002",
                }
            },
        )
        self.assertEqual(reserve.status_code, 200)
        self.assertEqual(reserve.get_json()["data"]["errorCode"], "NO_AVAILABILITY")

    def test_cancel_reservation_releases_hold(self):
        reserve = self.client.post("/gyg/1/reserve", headers=self.headers, json={
            "data": {
                "bookingItems": [{"category": "ADULT", "count": 2}],
                "dateTime": "2026-12-12T03:00:00+02:00",
                "productId": PRODUCT_ID,
                "gygBookingReference": "GYGHOLD001",
            }
        })
        ref = reserve.get_json()["data"]["reservationReference"]
        cancel = self.client.post(
            "/gyg/1/cancel-reservation",
            headers=self.headers,
            json={"data": {"reservationReference": ref, "gygBookingReference": "GYGHOLD001"}},
        )
        self.assertEqual(cancel.status_code, 200)
        store = GYGStore(db_path=self._tmp.name)
        self.assertEqual(store.held_pax(PRODUCT_ID, "2026-12-12", "2026-12-12T03:00"), 0)


if __name__ == "__main__":
    unittest.main()
