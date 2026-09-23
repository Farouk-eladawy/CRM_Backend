"""
End-to-end Tiqets supplier API test on the Windows/RDP server.

Usage (from repo root, after ai_agent is running):
  python tools/tiqets_full_flow_test.py
  python tools/tiqets_full_flow_test.py --public
  python tools/tiqets_full_flow_test.py --dry-run

Requires: tiqets_api on :5005 (started by ai_agent), Airtable catalog + ticket pool.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
import uuid

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import tiqets_api as t  # noqa: E402


def step(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Tiqets /v2 full flow test")
    parser.add_argument("--public", action="store_true", help="Use https://api.ftstravels.com instead of localhost:5005")
    parser.add_argument("--dry-run", action="store_true", help="Stop after reservation (no ticket pull / Airtable booking confirm)")
    args = parser.parse_args()

    cfg = t.load_tiqets_config()
    api_key = t.resolve_tiqets_api_key(cfg)
    base = "https://api.ftstravels.com" if args.public else "http://127.0.0.1:5005"
    headers = {"API-Key": api_key, "Content-Type": "application/json"}
    audio_base = str(cfg.get("audio_guide_base_url") or "http://tiqets.ftstravels.com/?GM/ticketId=")

    print("Base URL:", base)
    print("API key configured in config/booking_platforms:", bool(str(cfg.get("api_key") or "").strip()))
    print("Audio guide URL prefix:", audio_base)

    step("1) Health")
    health_path = "/health" if not args.public else "/v2/products"
    r = requests.get(f"{base}{health_path}", headers=headers if args.public else None, timeout=30)
    print("HTTP", r.status_code, r.text[:500])

    step("2) Products catalog GET /v2/products")
    r = requests.get(f"{base}/v2/products", headers=headers, timeout=30)
    print("HTTP", r.status_code)
    if r.status_code != 200:
        print(r.text[:500])
        return 1
    products = r.json()
    if not products:
        print("No active products in Products_Catalog (Active=1).")
        return 1
    product_id = products[0]["id"]
    print("Using product_id:", product_id)

    start = datetime.date.today().strftime("%Y-%m-%d")
    end = (datetime.date.today() + datetime.timedelta(days=3)).strftime("%Y-%m-%d")

    step(f"3) Availability GET /v2/products/{product_id}/availability")
    r = requests.get(
        f"{base}/v2/products/{product_id}/availability",
        headers=headers,
        params={"start": start, "end": end},
        timeout=30,
    )
    print("HTTP", r.status_code)
    print(json.dumps(r.json(), indent=2)[:2000])

    step("4) Reservation POST /v2/products/{id}/reservation")
    reservation_payload = {
        "datetime": f"{start}T10:00",
        "tickets": [{"variant_id": "ADT", "quantity": 1}],
        "customer": {
            "first_name": "API",
            "last_name": "Test",
            "email": "api.test@ftstravels.com",
            "phone": "+201000000000",
            "country": "eg",
        },
    }
    r = requests.post(
        f"{base}/v2/products/{product_id}/reservation",
        headers=headers,
        json=reservation_payload,
        timeout=30,
    )
    print("HTTP", r.status_code)
    res_data = r.json()
    print(json.dumps(res_data, indent=2))
    if r.status_code != 200:
        return 1
    reservation_id = res_data.get("reservation_id")
    print("Reservation ID:", reservation_id)

    if args.dry_run:
        print("\nDry-run: skipped booking confirm. Check Airtable List for", reservation_id)
        return 0

    order_reference = f"TIQ-TEST-{uuid.uuid4().hex[:8].upper()}"
    expected_audio = f"{audio_base}{order_reference}"
    print("\nExpected Audio Guide URL after confirm (if Has Audio Guide=true in catalog):")
    print(expected_audio)
    print("(Same pattern as Airtable formula: Audio Guide Link = prefix + Booking Nr.)")

    step("5) Booking confirm POST /v2/booking (pulls tickets from pool)")
    time.sleep(2)
    booking_payload = {"reservation_id": reservation_id, "order_reference": order_reference}
    r = requests.post(f"{base}/v2/booking", headers=headers, json=booking_payload, timeout=60)
    print("HTTP", r.status_code)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
    print(json.dumps(body, indent=2)[:3000])

    if r.status_code == 200:
        tickets = (body.get("tickets") or {}).get("ADT") or []
        print("\nBarcode / URL entries returned to Tiqets:", len(tickets))
        for i, entry in enumerate(tickets, 1):
            print(f"  {i}. {entry}")
        if any("tiqets.ftstravels.com" in str(x) for x in tickets):
            print("\nAudio guide URL present in API response.")
        else:
            print("\nNo audio guide URL in response (set Has Audio Guide on product in Products_Catalog).")
        print("\nVerify Airtable List: Booking Nr. =", order_reference)
        print("Formula Audio Guide Link should match:", expected_audio)
        return 0

    print("\nBooking failed — common causes: no free tickets in pool (Booking empty), wrong Tickets View.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
