"""Merge browser-extracted GYG product details into catalog + API JSON files."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from build_gyg_products_from_portal import build_api_product, PORTAL_CATALOG_FILE, PRODUCTS_FILE

LIST_META = [
    {"tour_id": "1441222", "title": "Serabit El-Khadim Bedouin Camp & 4x4 Desert Safari Adventure", "reference": "T-1441222"},
    {"tour_id": "1442388", "title": "Cairo: Private Guided Tour to Your Chosen Attraction", "reference": "T-1442388"},
    {"tour_id": "1439459", "title": "Luxor: Private Customizable Tour with Egyptologist Guide", "reference": "T-1439459"},
    {"tour_id": "1440408", "title": "Private Customizable Day Tour to Alexandria from Cairo", "reference": "T-1440408"},
    {"tour_id": "1441127", "title": "Mount Moses, St. Catherine Monastery & Stargazing Adventure", "reference": "T-1441127"},
    {"tour_id": "1361854", "title": "From Cairo: 4x4 Desert Safari, Waterfalls & Magic Lake", "reference": "T-1361854"},
    {"tour_id": "1191624", "title": "Hurghada: Luxor Valley of the Kings & Tutankhamun Tomb Trip", "reference": "T-1191624"},
    {"tour_id": "1195743", "title": "Hurghada: Cairo Day Trip with Pyramids, Museum & Quad Bike", "reference": "T-1195743"},
    {"tour_id": "1279014", "title": "Hurghada: City Tour & Bazaar with Optional Sand Museum Visit", "reference": "T-1279014"},
    {"tour_id": "1196475", "title": "Hurghada to Cairo: Pyramids & Museum for First-Time Visitors", "reference": "T-1196475"},
    {"tour_id": "1273778", "title": "Discover Cairo, Great Pyramids & Quad Bike From Sharm By Bus", "reference": "T-31032026"},
    {"tour_id": "1303745", "title": "Hurghada: Luxor Karnak, Hatshepsut & the Valley of the Kings", "reference": "T-1303745"},
    {"tour_id": "1361847", "title": "Luxor to Cairo: 2Day with Sleeper Train & Pyramids View Stay", "reference": "T-1361847"},
    {"tour_id": "1361217", "title": "Marsa Alam : Cairo 2-Day Tour with Luxury Pyramids View Stay", "reference": "T-1361217"},
    {"tour_id": "1344400", "title": "Sharm El Sheikh: Cairo 2-Day with Luxury Pyramids View Stay", "reference": "T-1344400"},
    {"tour_id": "1289272", "title": "Hurghada: Cairo 2-Day Tour with Luxury Pyramids View Stay", "reference": "T-1289272"},
    {"tour_id": "1289286", "title": "From Hurghada: Hidden Cairo , Pyramids & Cave Church", "reference": "T-1289286"},
    {"tour_id": "1286076", "title": "Ras Mohamed Half-Day Adventure The Hidden Paradise Escape", "reference": "T-1286076"},
    {"tour_id": "1278978", "title": "Sharm Signature: Mosque, Cathedral, Farsha Café & Old Market", "reference": "T-1278978"},
    {"tour_id": "1278027", "title": "Sharm: 3 Pools Dahab Tour, Quad, Camel, Red Canyon & Lunch", "reference": "T-1278027"},
    {"tour_id": "1195076", "title": "Sharm El-Sheikh: Jeep Adventure to Blue Hole, Canyon & Dahab", "reference": "T-1195076"},
    {"tour_id": "1195745", "title": "Hurghada: Full-Day Trip to Cairo by Plane", "reference": "T-1195745"},
]


def main(raw_path: str) -> None:
    with open(raw_path, encoding="utf-8") as handle:
        raw = json.load(handle)

    by_id = {str(item.get("gyg_tour_id") or item.get("tour_id")): item for item in raw.get("products", raw)}

    catalog = []
    api_products = []
    for row in LIST_META:
        tour_id = row["tour_id"]
        details = by_id.get(tour_id, {})
        list_row = {
            "title": row["title"],
            "reference": details.get("reference_code") or row["reference"],
            "gyg_tour_id": tour_id,
            "rating": "Not rated",
            "status": "Bookable",
            "public_url": details.get("public_url") or "",
            "supplier_url": f"https://supplier.getyourguide.com/products/details?tour_id={tour_id}",
        }
        merged = {**list_row, **details, "details_loaded": details.get("details_loaded", False)}
        catalog.append(merged)
        if details.get("details_loaded"):
            api_products.append(build_api_product(list_row, details))

    scraped_at = datetime.now(timezone.utc).isoformat()
    with open(PORTAL_CATALOG_FILE, "w", encoding="utf-8") as handle:
        json.dump({"scraped_at": scraped_at, "source": "browser_cdp", "count": len(catalog), "products": catalog}, handle, ensure_ascii=False, indent=2)

    with open(PRODUCTS_FILE, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "supplier_id": "fts-travels",
                "supplier_name": "FTS Travels",
                "currency": "EUR",
                "source": {"portal_url": "browser_cdp", "scraped_at": scraped_at, "catalog_count": len(api_products)},
                "products": api_products,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )

    loaded = sum(1 for p in catalog if p.get("details_loaded"))
    print(f"Merged {loaded}/{len(catalog)} products -> {PRODUCTS_FILE}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gyg_browser_scraped_raw.json")
