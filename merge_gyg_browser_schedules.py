"""Merge gyg_browser_schedules_raw.json into catalog + products."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from build_gyg_products_from_portal import (
    PORTAL_CATALOG_FILE,
    PRODUCTS_FILE,
    _save_outputs,
    _summarize_schedule_data,
    build_api_product,
)

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW_FILE = os.path.join(ROOT, "gyg_browser_schedules_raw.json")


def main() -> None:
    with open(RAW_FILE, encoding="utf-8") as handle:
        raw = json.load(handle)
    with open(PORTAL_CATALOG_FILE, encoding="utf-8") as handle:
        doc = json.load(handle)
    catalog = list(doc.get("products") or [])

    by_tour: dict[str, dict] = {}
    for entry in raw.get("products") or []:
        tid = str(entry.get("gyg_tour_id") or "")
        if tid:
            by_tour[tid] = entry

    api_products = []
    filled = 0
    for row in catalog:
        tid = str(row.get("gyg_tour_id") or "")
        extracted = by_tour.get(tid)
        if extracted:
            option_map = {
                str(opt.get("option_id")): opt
                for opt in (extracted.get("option_schedules") or [])
                if opt.get("option_id")
            }
            option_schedules = []
            for opt in row.get("options") or []:
                oid = str(opt.get("option_id") or "")
                found = option_map.get(oid) or {"option_id": oid, "cutoff_hours": 0, "schedules": []}
                option_schedules.append({
                    "option_id": oid,
                    "cutoff_hours": int(found.get("cutoff_hours") or 0),
                    "schedules": list(found.get("schedules") or []),
                })
            if not option_schedules and extracted.get("option_schedules"):
                option_schedules = list(extracted["option_schedules"])
            summary = _summarize_schedule_data(option_schedules)
            row["option_schedules"] = option_schedules
            row["schedule_summary"] = summary
            row["schedules_loaded"] = any(opt.get("schedules") for opt in option_schedules)
            row["schedules_scraped_at"] = datetime.now(timezone.utc).isoformat()
            if row["schedules_loaded"]:
                filled += 1
        list_row = {
            "title": row.get("title") or row.get("product_title") or "",
            "reference": row.get("reference_code") or row.get("reference") or "",
            "gyg_tour_id": tid,
            "rating": row.get("rating") or "Not rated",
            "status": row.get("status") or "Bookable",
            "public_url": row.get("public_url") or "",
            "supplier_url": row.get("supplier_url") or "",
        }
        if row.get("details_loaded"):
            api_products.append(build_api_product(list_row, row))

    _save_outputs(catalog, api_products)
    print(f"Merged {filled}/{len(catalog)} products with schedule data")
    print(f"Saved -> {PORTAL_CATALOG_FILE}")
    print(f"Saved -> {PRODUCTS_FILE}")


if __name__ == "__main__":
    main()
