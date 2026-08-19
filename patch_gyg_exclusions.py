"""Remove inclusion duplicates from exclusions in GYG catalog files."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from build_gyg_products_from_portal import PRODUCTS_FILE, PORTAL_CATALOG_FILE, build_api_product, _save_outputs

ROOT = os.path.dirname(os.path.abspath(__file__))


def dedupe_exclusions(product: dict) -> tuple[dict, int]:
    inclusions = product.get("inclusions") or []
    exclusions = product.get("exclusions") or []
    inc_lower = {item.lower() for item in inclusions}
    cleaned = [item for item in exclusions if item.lower() not in inc_lower]
    removed = len(exclusions) - len(cleaned)
    if removed:
        product = {**product, "exclusions": cleaned}
    return product, removed


def main() -> None:
    with open(PORTAL_CATALOG_FILE, encoding="utf-8") as handle:
        doc = json.load(handle)
    catalog = list(doc.get("products") or [])
    total_removed = 0
    fixed_ids: list[str] = []
    for idx, product in enumerate(catalog):
        updated, removed = dedupe_exclusions(product)
        if removed:
            total_removed += removed
            fixed_ids.append(str(updated.get("gyg_tour_id", "")))
            catalog[idx] = updated
    doc["scraped_at"] = datetime.now(timezone.utc).isoformat()
    doc["products"] = catalog
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
    print(f"Fixed {len(fixed_ids)} products, removed {total_removed} duplicate exclusion items")
    if fixed_ids:
        print("Tour IDs:", ", ".join(fixed_ids))


if __name__ == "__main__":
    main()
