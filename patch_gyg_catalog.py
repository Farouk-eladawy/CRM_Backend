"""Patch gyg_portal_catalog.json + gyg_products.json with new browser-extracted details."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

from build_gyg_products_from_portal import build_api_product, PORTAL_CATALOG_FILE, PRODUCTS_FILE


def main(raw_path: str) -> None:
    with open(raw_path, encoding="utf-8") as handle:
        raw = json.load(handle)
    new_by_id = {str(p["gyg_tour_id"]): p for p in raw.get("products", []) if p.get("details_loaded")}

    with open(PORTAL_CATALOG_FILE, encoding="utf-8") as handle:
        catalog_doc = json.load(handle)

    catalog = catalog_doc.get("products", [])
    for idx, row in enumerate(catalog):
        tour_id = str(row.get("gyg_tour_id") or "")
        if tour_id not in new_by_id:
            continue
        details = new_by_id[tour_id]
        catalog[idx] = {**row, **details, "details_loaded": True}
        catalog[idx].pop("error", None)

    scraped_at = datetime.now(timezone.utc).isoformat()
    catalog_doc["scraped_at"] = scraped_at
    catalog_doc["source"] = "browser_cdp_session"
    catalog_doc["products"] = catalog

    api_products = []
    for row in catalog:
        if not row.get("details_loaded"):
            continue
        list_row = {
            "title": row.get("title") or row.get("product_title") or "",
            "reference": row.get("reference_code") or row.get("reference") or "",
            "gyg_tour_id": row.get("gyg_tour_id"),
            "rating": row.get("rating") or "Not rated",
            "status": row.get("status") or "Bookable",
            "public_url": row.get("public_url") or "",
            "supplier_url": row.get("supplier_url") or "",
        }
        api_products.append(build_api_product(list_row, row))

    with open(PORTAL_CATALOG_FILE, "w", encoding="utf-8") as handle:
        json.dump(catalog_doc, handle, ensure_ascii=False, indent=2)

    with open(PRODUCTS_FILE, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "supplier_id": "fts-travels",
                "supplier_name": "FTS Travels",
                "currency": "EUR",
                "source": {
                    "portal_url": "browser_cdp_session",
                    "scraped_at": scraped_at,
                    "catalog_count": len(api_products),
                },
                "products": api_products,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )

    loaded = sum(1 for p in catalog if p.get("details_loaded"))
    print(f"Patched catalog: {loaded}/{len(catalog)} loaded, {len(api_products)} API products")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gyg_browser_scraped_raw.json")
