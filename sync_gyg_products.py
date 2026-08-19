"""Sync gyg_products.json from gyg_portal_catalog.json."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from build_gyg_products_from_portal import PORTAL_CATALOG_FILE, PRODUCTS_FILE, _save_outputs, build_api_product

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    with open(PORTAL_CATALOG_FILE, encoding="utf-8") as handle:
        doc = json.load(handle)
    catalog = list(doc.get("products") or [])
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
    _save_outputs(catalog, api_products)
    print(f"Synced {len(api_products)} products -> {PRODUCTS_FILE}")


if __name__ == "__main__":
    main()
