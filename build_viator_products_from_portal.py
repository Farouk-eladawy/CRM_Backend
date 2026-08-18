"""Build viator_products.json from the supplier portal Product List + local catalogs.

Only FTS Travels products (supplier 14976) are included. Product codes like 14976P97
are Viator *products*, not options. BASIC is a placeholder option until Manage-page
options are scraped from the supplier portal.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
FTS_PREFIX = "14976P"

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


def _dedupe_portal() -> list[dict]:
    seen = set()
    rows = []
    for row in PORTAL_ACTIVE:
        if row["code"] in seen:
            continue
        seen.add(row["code"])
        rows.append(row)
    return rows


PORTAL_ROWS = _dedupe_portal()


def is_placeholder_title(title: str) -> bool:
    text = str(title or "").strip()
    return not text or text.lower() in {"unknown title", "unknown", "n/a", "null"}


def title_from_url(url: str) -> str:
    parts = [part for part in str(url or "").split("/") if part]
    slug = ""
    for idx, part in enumerate(parts):
        if part.lower() == "tours" and idx + 2 < len(parts):
            slug = parts[idx + 2]
            break
    if not slug or re.match(r"^d\d+", slug, re.I):
        return ""
    slug = re.sub(r"-d\d+-\d+P\d+$", "", slug, flags=re.I)
    text = re.sub(r"[-_]+", " ", slug).strip()
    if not text:
        return ""
    return " ".join(word if word.isupper() else word.capitalize() for word in text.split())


def city_from_url(url: str) -> str:
    parts = [part for part in str(url or "").split("/") if part]
    for idx, part in enumerate(parts):
        if part.lower() == "tours" and idx + 1 < len(parts):
            return parts[idx + 1].replace("-", " ")
    return ""


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
    if "aswan" in blob:
        return "ASW", "Aswan"
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


def capacity(item: dict, title: str) -> int:
    features = item.get("features") or {}
    if features.get("max_travelers"):
        try:
            return max(1, int(features["max_travelers"]))
        except (TypeError, ValueError):
            pass
    blob = title.lower()
    if features.get("private_tour") or "private" in blob or "transfer" in blob:
        return 8
    if "cruise" in blob or "island" in blob or "boat" in blob or "snorkel" in blob:
        return 40
    return 15


def money(value, fallback=0.0) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return float(fallback)


def load_json_list(filename: str) -> list:
    path = os.path.join(ROOT, filename)
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


def resolve_title(info: dict, fallbacks: list[dict]) -> tuple[str, str]:
    url = str(info.get("url") or "")
    # Prefer the Viator.com URL slug over Bokun names: Bokun sometimes maps the
    # same 14976P code to a different activity.
    candidates = [
        ("catalog", info.get("title")),
        ("url", title_from_url(url)),
    ]
    for extra in fallbacks:
        extra_info = extra.get("tour_info") or extra
        candidates.append(("bokun", extra_info.get("title")))
        if extra_info.get("url"):
            candidates.append(("url", title_from_url(extra_info.get("url"))))
    for source, title in candidates:
        if not is_placeholder_title(title):
            return str(title).strip(), source
    return "", "missing"


def resolve_location(info: dict, title: str, fallbacks: list[dict]) -> str:
    url = str(info.get("url") or "")
    city = city_from_url(url)
    loc = str(info.get("location") or "").strip()
    if city and (not loc or loc.lower() in {"egypt", "eg", "tr", "hk"}):
        loc = f"{city}, Egypt"
    for extra in fallbacks:
        extra_info = extra.get("tour_info") or extra
        extra_city = city_from_url(extra_info.get("url") or "")
        extra_loc = str(extra_info.get("location") or "").strip()
        if extra_city and (not loc or loc.lower() in {"egypt", "eg"}):
            loc = f"{extra_city}, Egypt"
        elif extra_loc and extra_loc.lower() not in {"egypt", "eg"} and (not loc or loc.lower() in {"egypt", "eg"}):
            loc = extra_loc
    dest_code, dest_name = dest_from_location(loc, title)
    return loc if loc and loc.lower() not in {"egypt", "eg"} else f"{dest_name}, Egypt"


def better_item(primary: dict, extras: list[dict]) -> dict:
    """Prefer a priced / titled catalog row when merging Viator + Bokun scrapes."""
    ranked = [primary] + extras
    def score(item: dict) -> tuple:
        info = item.get("tour_info") or {}
        title_ok = 0 if is_placeholder_title(info.get("title")) else 1
        price = money((item.get("pricing") or {}).get("price_from"), 0)
        desc = str((item.get("overview") or {}).get("description") or "")
        desc_ok = 0 if is_placeholder_title(desc) or desc.lower().startswith("experience unknown") else 1
        return (title_ok, desc_ok, price)
    ranked.sort(key=score, reverse=True)
    return ranked[0]


def build_option(code: str, name: str, departure: str | None, retail: float, has_child: bool) -> dict:
    net = round(retail * 0.75, 2)
    child_retail = round(retail * 0.7, 2) if has_child else retail
    child_net = round(child_retail * 0.75, 2)
    hhmm = (departure or "00:00:00").replace(":", "")[:4]
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


def from_catalog_item(item: dict, portal_codes: set[str], extras: list[dict] | None = None) -> dict | None:
    extras = extras or []
    chosen = better_item(item, extras)
    info = chosen.get("tour_info") or {}
    code = str(info.get("product_code") or (item.get("tour_info") or {}).get("product_code") or "").strip()
    if not code.startswith(FTS_PREFIX):
        return None
    title, title_source = resolve_title(item.get("tour_info") or {}, extras)
    if is_placeholder_title(title):
        title, title_source = resolve_title(info, extras)
    location = resolve_location(item.get("tour_info") or info, title, extras + [item])
    dest_code, dest_name = dest_from_location(location, title)
    overview = chosen.get("overview") or {}
    pricing = chosen.get("pricing") or {}
    features = chosen.get("features") or {}
    retail = money(pricing.get("price_from"), 0)
    if retail <= 0:
        for extra in extras + [item]:
            extra_price = money(((extra.get("pricing") or {}).get("price_from")), 0)
            if extra_price > 0:
                retail = extra_price
                break
    departure = parse_start_time(overview.get("start_time") or (chosen.get("meeting_and_pickup") or {}).get("start_time"))
    option_name = "Hotel pickup included" if features.get("pickup_offered") else "Standard"
    description = str(overview.get("description") or title)
    if is_placeholder_title(description) or description.lower().startswith("experience unknown"):
        description = title
    return {
        "supplier_product_code": code,
        "supplier_product_name": title or code,
        "viator_product_code": code,
        "live": True,
        "api_connected": False,
        "pilot": code == "14976P3",
        "confirmed_on_supplier_portal": code in portal_codes,
        "title_source": title_source,
        "country_code": "EG",
        "destination_code": dest_code,
        "destination_name": dest_name,
        "location": location or f"{dest_name}, Egypt",
        "tour_description": description[:400],
        "languages": overview.get("languages") or [],
        "duration": overview.get("duration") or "",
        "pickup_offered": bool(features.get("pickup_offered")),
        "private_tour": bool(features.get("private_tour")),
        "daily_capacity": capacity(chosen, title),
        "cutoff_hours": cutoff_hours(chosen),
        "closed_weekdays": [],
        "blockout_dates": [],
        "options": [build_option(code, option_name, departure, retail or 40.0, bool(pricing.get("discounted_rates_for_kids")))],
    }


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
        "title_source": "portal",
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


def index_by_code(rows: list) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for item in rows:
        code = str((item.get("tour_info") or {}).get("product_code") or "").strip()
        if not code.startswith(FTS_PREFIX):
            continue
        grouped.setdefault(code, []).append(item)
    return grouped


def main():
    portal_codes = {row["code"] for row in PORTAL_ROWS}
    viator_catalog = load_json_list("Viator_data.json")
    bokun_catalog = load_json_list("Viator_data_bokun.json")
    bokun_by_code = index_by_code(bokun_catalog)

    by_code = {}
    skipped_foreign = 0
    for item in viator_catalog:
        code = str((item.get("tour_info") or {}).get("product_code") or "").strip()
        if not code:
            continue
        if not code.startswith(FTS_PREFIX):
            skipped_foreign += 1
            continue
        product = from_catalog_item(item, portal_codes, bokun_by_code.get(code) or [])
        if product:
            by_code[code] = product

    for code, extras in bokun_by_code.items():
        if code in by_code:
            continue
        product = from_catalog_item(extras[0], portal_codes, extras[1:])
        if product:
            by_code[code] = product

    for row in PORTAL_ROWS:
        if row["code"] not in by_code:
            by_code[row["code"]] = from_portal_row(row)
        else:
            existing = by_code[row["code"]]
            existing["confirmed_on_supplier_portal"] = True
            existing["live"] = True
            if is_placeholder_title(existing.get("supplier_product_name")):
                existing["supplier_product_name"] = row["title"]
                existing["title_source"] = "portal"
            existing["location"] = row["location"]
            dest_code, dest_name = dest_from_location(row["location"], row["title"])
            existing["destination_code"] = dest_code
            existing["destination_name"] = dest_name

    ordered = []
    seen = set()
    for row in PORTAL_ROWS:
        ordered.append(by_code[row["code"]])
        seen.add(row["code"])
    for code in sorted(by_code.keys(), key=lambda c: int(re.sub(r"\D", "", c) or 0), reverse=True):
        if code not in seen:
            ordered.append(by_code[code])

    payload = {
        "_comment": "FTS Travels supplier 14976 only. Codes like 14976P97 are products, not options; BASIC is a placeholder option until portal Manage data is scraped. live=true products appear in Tour List. api_connected stays false until Product Connection is saved after Supplier API certification.",
        "supplier_id": 14976,
        "supplier_name": "FTS Travels",
        "currency": "USD",
        "source": {
            "portal_url": "https://supplier.viator.com/products/",
            "scraped_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "portal_active_count": len(PORTAL_ROWS),
            "catalog_count": len(ordered),
            "skipped_foreign_products": skipped_foreign,
        },
        "products": ordered,
    }
    out_path = os.path.join(ROOT, "viator_products.json")
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    unknown = sum(1 for p in ordered if is_placeholder_title(p.get("supplier_product_name")))
    print(f"Wrote {len(ordered)} FTS products to {out_path}")
    print(f"Portal-confirmed: {sum(1 for p in ordered if p.get('confirmed_on_supplier_portal'))}")
    print(f"Skipped foreign: {skipped_foreign}")
    print(f"Unknown titles remaining: {unknown}")


if __name__ == "__main__":
    main()
