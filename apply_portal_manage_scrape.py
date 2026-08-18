"""Merge supplier-portal Manage scrapes into viator_products.json."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))


def parse_times(raw: str) -> list[str]:
    out = []
    for hour, minute, ampm in re.findall(r"(\d{1,2}):(\d{2})\s*(am|pm)", raw or "", re.I):
        h = int(hour)
        m = int(minute)
        ap = ampm.lower()
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        out.append(f"{h:02d}:{m:02d}:00")
    return out


def money(value) -> float:
    try:
        return round(float(str(value).replace(",", "").split()[-1]), 2)
    except (TypeError, ValueError):
        return 0.0


def net_from_retail(retail: float, commission: float) -> float:
    return round(retail * (1 - (commission or 0) / 100.0), 2)


def option_row(code: str, opt: dict, commission: float) -> dict:
    adult = money(opt.get("adult_retail"))
    child = money(opt.get("child_retail"))
    infant = money(opt.get("infant_retail"))
    times = opt.get("departure_times") or parse_times(opt.get("times") or "")
    opt_code = str(opt.get("code") or "BASIC").strip()
    return {
        "supplier_option_code": opt_code,
        "supplier_option_name": str(opt.get("name") or opt_code).strip(),
        "product_option_id": f"{code}:{opt_code}",
        "portal_option_id": opt.get("portal_option_id") or "",
        "departure_times": times,
        "adult_retail": adult,
        "adult_net": net_from_retail(adult, commission),
        "child_retail": child,
        "child_net": net_from_retail(child, commission),
        "infant_retail": infant,
        "infant_net": net_from_retail(infant, commission),
    }


def apply_scrape(product: dict, scrape: dict) -> dict:
    code = scrape["code"]
    commission = float(scrape.get("commission_rate") or 22)
    merged = dict(product)
    merged.update({
        "supplier_product_code": code,
        "viator_product_code": code,
        "supplier_product_name": scrape.get("title") or product.get("supplier_product_name"),
        "live": True,
        "api_connected": False,
        "confirmed_on_supplier_portal": True,
        "title_source": "portal_manage",
        "cutoff_hours": int(scrape["cutoff_hours"] if scrape.get("cutoff_hours") is not None else (product.get("cutoff_hours") if product.get("cutoff_hours") is not None else 24)),
        "confirmation_type": scrape.get("confirmation_type") or "instant",
        "start_times_mode": bool(scrape.get("start_times_mode", True)),
        "commission_rate": commission,
        "max_travelers_per_booking": int(scrape.get("max_travelers_per_booking") or 15),
        "daily_capacity": int(scrape.get("daily_capacity") or product.get("daily_capacity") or 15),
        "pickup_offered": scrape.get("pickup_offered", True),
        "ticket_scope": scrape.get("ticket_scope") or "per_booking",
        "barcode_from_reservation_system": bool(scrape.get("barcode_from_reservation_system", False)),
        "booking_questions": scrape.get("booking_questions") or product.get("booking_questions") or [],
        "age_bands": scrape.get("age_bands") or product.get("age_bands") or {},
        "portal_connection": scrape.get("portal_connection") or product.get("portal_connection") or {},
        "options": [option_row(code, opt, commission) for opt in (scrape.get("options") or [])],
    })
    if scrape.get("duration"):
        merged["duration"] = scrape["duration"]
    if scrape.get("location"):
        merged["location"] = scrape["location"]
    return merged


def main():
    scrape_path = os.path.join(ROOT, "portal_manage_scrape.json")
    catalog_path = os.path.join(ROOT, "viator_products.json")
    with open(scrape_path, "r", encoding="utf-8") as handle:
        scrapes = json.load(handle)
    with open(catalog_path, "r", encoding="utf-8") as handle:
        catalog = json.load(handle)
    products = catalog.get("products") or []
    by_code = {p.get("supplier_product_code"): p for p in products}
    applied = 0
    for scrape in scrapes.get("products") or []:
        code = scrape.get("code")
        if not code:
            continue
        by_code[code] = apply_scrape(by_code.get(code) or {"supplier_product_code": code}, scrape)
        applied += 1
    ordered = []
    seen = set()
    for product in products:
        code = product.get("supplier_product_code")
        ordered.append(by_code.get(code, product))
        seen.add(code)
    for code, row in by_code.items():
        if code not in seen:
            ordered.append(row)
    catalog["products"] = ordered
    catalog.setdefault("source", {})["manage_scraped_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    catalog["source"]["manage_scraped_count"] = applied
    with open(catalog_path, "w", encoding="utf-8") as handle:
        json.dump(catalog, handle, indent=2, ensure_ascii=False)
    print(f"Applied {applied} Manage scrapes")


if __name__ == "__main__":
    main()
