"""Scrape only missing GYG products using saved auth state."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright
from build_gyg_products_from_portal import scrape_product_details, STATE_FILE, PORTAL_CATALOG_FILE
from patch_gyg_catalog import main as patch_catalog

ROOT = os.path.dirname(os.path.abspath(__file__))
MISSING_IDS = [
    "1303745", "1361847", "1361217", "1344400", "1289272", "1289286",
    "1286076", "1278978", "1278027", "1195076", "1195745",
]
RAW_OUT = os.path.join(ROOT, "gyg_browser_scraped_raw.json")


def main() -> None:
    with open(PORTAL_CATALOG_FILE, encoding="utf-8") as handle:
        catalog = json.load(handle)
    rows_by_id = {str(p["gyg_tour_id"]): p for p in catalog.get("products", [])}

    extracted = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False)
        ctx_kwargs = {"viewport": {"width": 1400, "height": 900}}
        if os.path.isfile(STATE_FILE):
            ctx_kwargs["storage_state"] = STATE_FILE
        context = browser.new_context(**ctx_kwargs)
        page = context.new_page()
        page.goto("https://supplier.getyourguide.com/products/list?limit=100", timeout=60000)
        if "login" in page.url.lower():
            print("LOGIN REQUIRED: sign in in the opened browser window, waiting 120s...")
            for _ in range(60):
                if "login" not in page.url.lower():
                    break
                time.sleep(2)
            if "login" in page.url.lower():
                browser.close()
                sys.exit("Session expired — please log in to supplier portal and rerun.")

        for idx, tour_id in enumerate(MISSING_IDS, 1):
            title = rows_by_id.get(tour_id, {}).get("title", tour_id)
            print(f"[{idx}/{len(MISSING_IDS)}] {title} ({tour_id})")
            try:
                details = scrape_product_details(page, tour_id)
                extracted.append(details)
            except Exception as exc:
                print(f"  FAILED: {exc}")
            time.sleep(1)

        context.storage_state(path=STATE_FILE)
        context.close()
        browser.close()

    # merge with any prior browser raw
    prior = {"products": []}
    if os.path.isfile(RAW_OUT):
        with open(RAW_OUT, encoding="utf-8") as handle:
            prior = json.load(handle)
    by_id = {str(p["gyg_tour_id"]): p for p in prior.get("products", []) if p.get("gyg_tour_id")}
    for item in extracted:
        by_id[str(item["gyg_tour_id"])] = item
    with open(RAW_OUT, "w", encoding="utf-8") as handle:
        json.dump({"products": list(by_id.values())}, handle, ensure_ascii=False, indent=2)

    patch_catalog(RAW_OUT)
    print(f"Done — extracted {len(extracted)} new products")


if __name__ == "__main__":
    main()
