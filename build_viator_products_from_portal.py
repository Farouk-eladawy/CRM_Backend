"""Build viator_products.json from the supplier portal Product List + local Viator_data.json."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

# Confirmed Active + Fully connected on supplier.viator.com/products/ (first page, 2026-08-18)
PORTAL_ACTIVE = [
    {"code": "14976P156", "title": "Sharm El Sheikh Red Sea Beach Horse Riding Tour", "location": "Sharm El Sheikh, Egypt"},
    {"code": "14976P153", "title": "From Cairo: 4x4 Desert Safari, Waterfalls & Magic Lake", "location": "Cairo, Egypt"},
    {"code": "14976P152", "title": "Cairo Ancient Egypt Discovery with Immersive VR Experience", "location": "Cairo, Egypt"},
    {"code": "14976P151", "title": "Sahl Hasheesh Elite Beach Dive and Coral Reef Experience", "location": "Hurghada, Egypt"},
    {"code": "14976P150", "title": "Opal Nile Romantic Dinner Cruise with Optional Jetcar Adventure", "location": "Cairo, Egypt"},
    {"code": "14976P148", "title": "Sharm El Sheikh Cairo 2 Day Tour with Pyramids View Stay", "location": "Sharm El Sheikh, Egypt"},
    {"code": "14976P147", "title": "Cairo Pyramids & Sphinx Adventure with Camel Ride & Optional ATV", "location": "Cairo, Egypt"},
    {"code": "14976P146", "title": "Hurghada: Cairo 2-Day Tour with Luxury Pyramids View Stay", "location": "Hurghada, Egypt"},
    {"code": "14976P144", "title": "Hurghada to Luxor Karnak, Hatshepsut & the Valley of the Kings", "location": "Hurghada, Egypt"},
    {"code": "14976P143", "title": "Nunia Aquarena Makadi Bay Water Park From Hurghada", "location": "Hurghada, Egypt"},
    {"code": "14976P142", "title": "Shagie Farms Eco-Tourism Strawberry Picking Experience from Cairo", "location": "Cairo, Egypt"},
    {"code": "14976P141", "title": "Private Luxor Day Tour W/Horse Carriage Ride & Flexible Itinerary", "location": "Luxor, Egypt"},
    {"code": "14976P139", "title": "Utopia - Bianca Island with Transfer and Lunch from Hurghada", "location": "Hurghada, Egypt"},
    {"code": "14976P135", "title": "Airport Private Transfer from Hurghada,Fast & Comfortable Service", "location": "Hurghada, Egypt"},
    {"code": "14976P133", "title": "Luxor and Abu Simbel 2-Day Private Tour from Hurghada", "location": "Hurghada, Egypt"},
    {"code": "14976P129", "title": "Dendera, Osireion & Abydos Full-Day Tour from Hurghada", "location": "Hurghada, Egypt"},
    {"code": "14976P127", "title": "Sea Turtles Marsa Mubarak, Boat trip with Snorkeling-Marsa Alam", "location": "Marsa Alam, Egypt"},
    {"code": "14976P126", "title": "Shaab Samadai, Snorkeling Adventure & Coral Reef at Marsa Alam", "location": "Marsa Alam, Egypt"},
    {"code": "14976P125", "title": "Luxor Tour to Valley of the Kings, Karnak Temples from Marsa Alam", "location": "Marsa Alam, Egypt"},
    {"code": "14976P124", "title": "From Sharm Elsheikh : The Lost City of Petra & Day Tour By Ferry", "location": "Sharm El Sheikh, Egypt"},
]


def dest_from_location(location: str, title: str = "") -> tuple[str, str]:
    blob = f"{location} {title}".lower()
    if "ras mohamed" in blob or "sharm" in blob:
        return "SSH", "Sharm"
    if "marsa alam" in blob:
        return "RMF", "Marsa Alam"
    if "luxor" in blob:
        return "LXR", "Luxor"
    if "cairo" in blob or "giza" in blob:
        return "CAI", "Cairo"
    if "hurghada" in blob or "makadi" in blob or "sahl hasheesh" in blob or "el gouna" in blob:
        return "HRG", "Hurghada"
    return "HRG", "Hurghada"


def parse_start_time(raw: str) -> str | None:
    text = str(raw or "").strip()
    if not text or re.search(r"varies|flexible|based on flight|pickup", text, re.I):
        return None
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text, re.I)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = (match.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if hour > 23:
        return None
    return f"{hour:02d}:{minute:02d}:00"


def cutoff_hours(item: dict) -> int:
    policy = ((item.get("cancellation_policy") or {}).get("free_cancellation") or "")
    match = re.search(r"(\d+)\s*hour", policy, re.I)
    if match:
        return int(match.group(1))
    return 24


def capacity(item: dict) -> int:
    features = item.get("features") or {}
    if features.get("max_travelers"):
        try:
            return max(1, int(features["max_travelers"]))
        except (TypeError, ValueError):
            pass
    title = ((item.get("tour_info") or {}).get("title") or "").lower()
    if features.get("private_tour") or "private" in title or "transfer" in title:
        return 8
    if "cruise" in title or "island" in title or "boat" in title or "snorkel" in title:
        return 40
    return 15


def money(value, fallback=0.0) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return float(fallback)


def build_option(code: str, name: str, departure: str | None, retail: float, has_child: bool) -> dict:
    net = round(retail * 0.75, 2)
    child_retail = round(retail * 0.7, 2) if has_child else retail
    child_net = round(child_retail * 0.75, 2)
    hhmm = (departure or "0000").replace(":", "")[:4]
    option = {
        "supplier_option_code": "BASIC",
        "supplier_option_name": name,
        "product_option_id": f"{code}:BASIC:{hhmm}",
        "adult_retail": retail,
        "adult_net": net,
        "child_retail": child_retail,
        "child_net": child_net,
        "infant_retail": 0.0,
        "infant_net": 0.0,
    }
    if departure:
        option["departure_time"] = departure
    return option


def from_catalog_item(item: dict, portal_codes: set[str]) -> dict:
    info = item.get("tour_info") or {}
    code = str(info.get("product_code") or "").strip()
    title = str(info.get("title") or "").strip()
    location = str(info.get("location") or "").strip()
    dest_code, dest_name = dest_from_location(location, title)
    overview = item.get("overview") or {}
    pricing = item.get("pricing") or {}
    features = item.get("features") or {}
    retail = money(pricing.get("price_from"), 0)
    departure = parse_start_time(overview.get("start_time") or (item.get("meeting_and_pickup") or {}).get("start_time"))
    option_name = "Hotel pickup included" if features.get("pickup_offered") else "Standard"
    product = {
        "supplier_product_code": code,
        "supplier_product_name": title,
        "viator_product_code": code,
        "live": True,
        "api_connected": False,
        "pilot": code == "14976P3",
        "confirmed_on_supplier_portal": code in portal_codes,
        "country_code": "EG",
        "destination_code": dest_code,
        "destination_name": dest_name,
        "location": location or f"{dest_name}, Egypt",
        "tour_description": str(overview.get("description") or title)[:400],
        "languages": overview.get("languages") or [],
        "duration": overview.get("duration") or "",
        "pickup_offered": bool(features.get("pickup_offered")),
        "private_tour": bool(features.get("private_tour")),
        "daily_capacity": capacity(item),
        "cutoff_hours": cutoff_hours(item),
        "closed_weekdays": [],
        "blockout_dates": [],
        "options": [build_option(code, option_name, departure, retail or 40.0, bool(pricing.get("discounted_rates_for_kids")))],
    }
    return product


def from_portal_row(row: dict) -> dict:
    code = row["code"]
    title = row["title"]
    location = row["location"]
    dest_code, dest_name = dest_from_location(location, title)
    return {
        "supplier_product_code": code,
        "supplier_product_name": title,
        "viator_product_code": code,
        "live": True,
        "api_connected": False,
        "pilot": False,
        "confirmed_on_supplier_portal": True,
        "country_code": "EG",
        "destination_code": dest_code,
        "destination_name": dest_name,
        "location": location,
        "tour_description": title,
        "languages": [],
        "duration": "",
        "pickup_offered": True,
        "private_tour": "private" in title.lower() or "transfer" in title.lower(),
        "daily_capacity": 8 if "private" in title.lower() or "transfer" in title.lower() else 15,
        "cutoff_hours": 24,
        "closed_weekdays": [],
        "blockout_dates": [],
        "options": [build_option(code, "Standard", None, 40.0, True)],
    }


def main():
    portal_codes = {row["code"] for row in PORTAL_ACTIVE}
    catalog_path = os.path.join(ROOT, "Viator_data.json")
    with open(catalog_path, "r", encoding="utf-8") as handle:
        catalog = json.load(handle)

    by_code = {}
    for item in catalog:
        code = str((item.get("tour_info") or {}).get("product_code") or "").strip()
        if not code:
            continue
        by_code[code] = from_catalog_item(item, portal_codes)

    for row in PORTAL_ACTIVE:
        if row["code"] not in by_code:
            by_code[row["code"]] = from_portal_row(row)
        else:
            by_code[row["code"]]["confirmed_on_supplier_portal"] = True
            by_code[row["code"]]["live"] = True

    # Keep portal-first order, then remaining catalog codes descending.
    ordered = []
    seen = set()
    for row in PORTAL_ACTIVE:
        ordered.append(by_code[row["code"]])
        seen.add(row["code"])
    for code in sorted(by_code.keys(), key=lambda c: int(re.sub(r"\D", "", c) or 0), reverse=True):
        if code not in seen:
            ordered.append(by_code[code])

    payload = {
        "_comment": "Generated from supplier.viator.com Product List (Active page) plus local Viator_data.json. Supplier ID 14976 = FTS Travels. live=true products appear in Tour List. api_connected remains false until Product Connection is saved in the Viator portal after Supplier API certification.",
        "supplier_id": 14976,
        "supplier_name": "FTS Travels",
        "currency": "USD",
        "source": {
            "portal_url": "https://supplier.viator.com/products/",
            "scraped_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "portal_active_count": len(PORTAL_ACTIVE),
            "catalog_count": len(ordered),
        },
        "products": ordered,
    }
    out_path = os.path.join(ROOT, "viator_products.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(f"Wrote {len(ordered)} products to {out_path}")
    print(f"Portal-confirmed: {sum(1 for p in ordered if p.get('confirmed_on_supplier_portal'))}")


if __name__ == "__main__":
    main()
