"""Unit tests for the Viator Supplier / Reservation System API."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from viator_supplier_api import create_test_app


TEST_KEY = "viator-test-api-key"
SUPPLIER_ID = 1004
OPTION_ID = "14976P3:BASIC:0400"


def _cfg(**extra):
    cfg = {
        "enabled": True,
        "api_key": TEST_KEY,
        "supplier_id": SUPPLIER_ID,
        "reseller_id": "1000",
        "environment": "sandbox",
        "async_airtable": False,
        "ip_allowlist": [],
        "products_file": "viator_products.json",
    }
    cfg.update(extra)
    return cfg


SAMPLE_BOOKING = {
    "requestType": "BookingRequest",
    "data": {
        "ApiKey": TEST_KEY,
        "ResellerId": "1000",
        "SupplierId": SUPPLIER_ID,
        "ExternalReference": "10051374722992645",
        "Timestamp": "2013-07-25T13:30:52.616+10:00",
        "BookingReference": "BR-1357708331",
        "TravelDate": "2026-12-10",
        "SupplierProductCode": "14976P3",
        "Location": "Hurghada, Egypt",
        "TourOptions": {
            "SupplierOptionCode": "BASIC",
            "SupplierOptionName": "Tour with Entry Fees",
            "TourDepartureTime": "04:00:00",
        },
        "CurrencyCode": "USD",
        "Amount": 126.00,
        "Traveller": [
            {
                "TravellerIdentifier": "1",
                "GivenName": "Emmanuel",
                "Surname": "MAS",
                "AgeBand": "Adult",
                "LeadTraveller": True,
            },
            {
                "TravellerIdentifier": "2",
                "GivenName": "Anna",
                "Surname": "MAS",
                "AgeBand": "Adult",
                "LeadTraveller": False,
            },
        ],
        "TravellerMix": {"Adult": 2, "Child": 0, "Youth": 0, "Infant": 0, "Senior": 0, "Total": 2},
        "RequiredInfo": {"Question": [{"QuestionText": "Language", "QuestionAnswer": "French"}]},
        "SpecialRequirement": "",
        "PickupPoint": "Hurghada, Red Sea Governorate, Egypt",
        "ContactDetail": {
            "ContactType": "ALTERNATE",
            "ContactName": "Emmanuel MAS",
            "ContactValue": "+33 6 88 92 12 82",
        },
        "ContactEmail": "MSG-test+BR-1357708331@expmessaging.tripadvisor.com",
    },
}


class ViatorSupplierApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.app = create_test_app(config_override=_cfg(), db_path=self._tmp.name)
        self.client = self.app.test_client()
        self.headers = {"X-Api-Key": TEST_KEY, "Content-Type": "application/json"}

    def tearDown(self):
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_health_does_not_require_auth(self):
        resp = self.client.get("/viator/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["status"], "ok")
        self.assertGreaterEqual(body["live_products"], 1)

    def test_invalid_api_key_is_rejected(self):
        resp = self.client.post(
            "/viator/tourlist",
            json={"requestType": "TourListRequest", "data": {"ApiKey": "wrong", "SupplierId": SUPPLIER_ID}},
        )
        self.assertEqual(resp.status_code, 401)

    def test_tour_list_returns_live_products_and_option_ids(self):
        resp = self.client.post(
            "/viator/tourlist",
            headers=self.headers,
            json={
                "requestType": "TourListRequest",
                "data": {"ApiKey": TEST_KEY, "ResellerId": "1000", "SupplierId": SUPPLIER_ID},
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["responseType"], "TourListResponse")
        self.assertEqual(body["data"]["RequestStatus"]["Status"], "SUCCESS")
        codes = [t["SupplierProductCode"] for t in body["data"]["Tour"]]
        self.assertIn("14976P3", codes)
        option_ids = [o["productOptionId"] for t in body["data"]["Tour"] for o in t["TourOption"]]
        self.assertIn(OPTION_ID, option_ids)

    def test_booking_creates_trip_and_is_idempotent(self):
        first = self.client.post("/viator/booking", headers=self.headers, json=SAMPLE_BOOKING)
        self.assertEqual(first.status_code, 200)
        data = first.get_json()["data"]
        self.assertEqual(data["RequestStatus"]["Status"], "SUCCESS")
        self.assertEqual(data["BookingReference"], "BR-1357708331")
        self.assertEqual(data["SupplierConfirmationNumber"], "FTS-BR-1357708331")
        self.assertEqual(data["TransactionStatus"]["Status"], "CONFIRMED")

        second = self.client.post("/viator/booking", headers=self.headers, json=SAMPLE_BOOKING)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.get_json()["data"]["SupplierConfirmationNumber"], "FTS-BR-1357708331")

        from viator_supplier_api import ViatorStore
        store = ViatorStore(db_path=self._tmp.name)
        with store._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM bookings WHERE booking_reference = ?", ("BR-1357708331",)).fetchone()[0]
        self.assertEqual(count, 1)

        row = store.get_booking("BR-1357708331")
        self.assertEqual(row["lead_name"], "Emmanuel MAS")
        self.assertEqual(row["adults"], 2)
        self.assertEqual(row["travel_date"], "2026-12-10")
        self.assertEqual(row["option_name"], "Hotel pickup included")
        self.assertEqual(row["pickup_point"], "Hurghada, Red Sea Governorate, Egypt")
        self.assertEqual(row["phone"], "+33688921282")
        self.assertEqual(row["net_amount"], 126.0)
        self.assertEqual(row["email"], "")  # proxy relay is not stored as personal email

    def test_amendment_updates_same_booking_reference(self):
        self.client.post("/viator/booking", headers=self.headers, json=SAMPLE_BOOKING)
        amend = json.loads(json.dumps(SAMPLE_BOOKING))
        amend["requestType"] = "BookingAmendmentRequest"
        amend["data"]["TravelDate"] = "2026-12-20"
        amend["data"]["TravellerMix"] = {"Adult": 1, "Child": 1, "Youth": 0, "Infant": 0, "Senior": 0, "Total": 2}
        amend["data"]["Traveller"] = [
            {"TravellerIdentifier": "1", "GivenName": "Emmanuel", "Surname": "MAS", "AgeBand": "Adult", "LeadTraveller": True},
            {"TravellerIdentifier": "2", "GivenName": "Leo", "Surname": "MAS", "AgeBand": "Child", "LeadTraveller": False},
        ]
        resp = self.client.post("/viator/booking-amendment", headers=self.headers, json=amend)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["data"]["RequestStatus"]["Status"], "SUCCESS")
        from viator_supplier_api import ViatorStore
        row = ViatorStore(db_path=self._tmp.name).get_booking("BR-1357708331")
        self.assertEqual(row["travel_date"], "2026-12-20")
        self.assertEqual(row["children"], 1)
        self.assertEqual(row["adults"], 1)
        self.assertEqual(row["status"], "AMENDED")

    def test_cancellation_marks_cancelled_and_frees_capacity(self):
        self.client.post("/viator/booking", headers=self.headers, json=SAMPLE_BOOKING)
        resp = self.client.post(
            "/viator/booking-cancellation",
            headers=self.headers,
            json={
                "requestType": "BookingCancellationRequest",
                "data": {
                    "ApiKey": TEST_KEY,
                    "SupplierId": SUPPLIER_ID,
                    "BookingReference": "BR-1357708331",
                    "CancelDate": "2026-08-17",
                    "Reason": "No longer traveling",
                },
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()["data"]
        self.assertEqual(body["RequestStatus"]["Status"], "SUCCESS")
        self.assertTrue(str(body["SupplierCancellationNumber"]).startswith("CXL-"))
        from viator_supplier_api import ViatorStore
        store = ViatorStore(db_path=self._tmp.name)
        self.assertEqual(store.get_booking("BR-1357708331")["status"], "CANCELLED")
        self.assertEqual(store.booked_pax("14976P3", "2026-12-10", "BASIC"), 0)

    def test_realtime_availability_sold_out_blocks_checkout(self):
        product_cfg = {
            "live": True,
            "supplier_product_code": "TINY",
            "supplier_product_name": "Tiny test tour",
            "country_code": "EG",
            "destination_code": "HRG",
            "destination_name": "Hurghada",
            "daily_capacity": 2,
            "cutoff_hours": 0,
            "options": [{
                "supplier_option_code": "BASIC",
                "supplier_option_name": "Basic",
                "product_option_id": "TINY:BASIC:0900",
                "departure_time": "09:00:00",
                "adult_retail": 10,
                "adult_net": 8,
                "child_retail": 5,
                "child_net": 4,
                "infant_retail": 0,
                "infant_net": 0,
            }],
        }
        products_path = self._tmp.name + ".products.json"
        with open(products_path, "w", encoding="utf-8") as handle:
            json.dump({"currency": "USD", "products": [product_cfg]}, handle)
        app = create_test_app(config_override=_cfg(products_file=products_path), db_path=self._tmp.name + ".tiny.db")
        client = app.test_client()
        booking = json.loads(json.dumps(SAMPLE_BOOKING))
        booking["data"]["SupplierProductCode"] = "TINY"
        booking["data"]["BookingReference"] = "BR-111"
        booking["data"]["TourOptions"]["TourDepartureTime"] = "09:00:00"
        booking["data"]["TravellerMix"] = {"Adult": 2, "Child": 0, "Youth": 0, "Infant": 0, "Senior": 0, "Total": 2}
        self.assertEqual(client.post("/viator/booking", headers=self.headers, json=booking).status_code, 200)

        avail = client.post(
            "/viator/availability",
            headers=self.headers,
            json={
                "requestType": "AvailabilityRequest",
                "data": {
                    "ApiKey": TEST_KEY,
                    "SupplierId": SUPPLIER_ID,
                    "StartDate": "2026-12-10",
                    "SupplierProductCode": "TINY",
                    "TourOptions": {"SupplierOptionCode": "BASIC", "TourDepartureTime": "09:00:00"},
                    "TravellerMix": {"Adult": 1, "Child": 0, "Youth": 0, "Infant": 0, "Senior": 0, "Total": 1},
                },
            },
        )
        status = avail.get_json()["data"]["TourAvailability"][0]["AvailabilityStatus"]
        self.assertEqual(status["Status"], "UNAVAILABLE")
        self.assertEqual(status["UnavailabilityReason"], "SOLD_OUT")

        check = client.post(
            "/viator/v2/availability/check",
            headers=self.headers,
            json={
                "supplierId": SUPPLIER_ID,
                "productOptions": [{"productOptionId": "TINY:BASIC:0900", "startTimes": ["09:00"]}],
                "travelDate": "2026-12-10",
                "tickets": [{"type": "ADULT", "quantity": 1}],
                "totalTravelers": 1,
            },
        )
        self.assertEqual(check.status_code, 200)
        self.assertEqual(check.get_json()["productOptions"][0]["events"][0]["status"], "SOLD_OUT")

    def test_v2_reserve_then_calendar(self):
        reserve = self.client.post(
            "/viator/v2/reserve",
            headers=self.headers,
            json={
                "supplierId": SUPPLIER_ID,
                "productOptionId": OPTION_ID,
                "startTime": "04:00",
                "travelDate": "2026-12-11",
                "tickets": [{"type": "ADULT", "quantity": 2}],
                "totalTravelers": 2,
            },
        )
        self.assertEqual(reserve.status_code, 200)
        body = reserve.get_json()
        self.assertEqual(body["status"], "RESERVED")
        self.assertTrue(body["reference"].startswith("HOLD-"))

        calendar = self.client.post(
            "/viator/v2/availability/calendar",
            headers=self.headers,
            json={
                "supplierId": SUPPLIER_ID,
                "productOptionIds": [OPTION_ID],
                "startDate": "2026-12-11",
                "endDate": "2026-12-11",
            },
        )
        self.assertEqual(calendar.status_code, 200)
        remaining = calendar.get_json()["productOptions"][0]["dates"][0]["events"][0]["capacity"]["remaining"]
        self.assertEqual(remaining, 13)  # 15 daily - 2 held

    def test_batch_availability_includes_pilot_product(self):
        resp = self.client.post(
            "/viator/batch-availability",
            headers=self.headers,
            json={
                "requestType": "BatchAvailabilityRequest",
                "data": {
                    "ApiKey": TEST_KEY,
                    "SupplierId": SUPPLIER_ID,
                    "StartDate": "2026-12-10",
                    "EndDate": "2026-12-10",
                    "Mode": "ALL",
                },
            },
        )
        self.assertEqual(resp.status_code, 200)
        rows = resp.get_json()["data"]["BatchTourAvailability"]
        codes = {row["SupplierProductCode"] for row in rows}
        self.assertIn("14976P3", codes)


if __name__ == "__main__":
    unittest.main()
