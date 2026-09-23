"""Compare Airtable Products_Catalog vs local import CSV + optional /v2/products."""
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import tiqets_api as t  # noqa: E402

OUT = Path(__file__).resolve().parent / "audit_tiqets_catalog_out.json"
CSV = Path(__file__).resolve().parent / "tiqets_products_catalog_import.csv"


def load_csv_expected():
    by_id = {}
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            by_id[row["Product ID"].strip()] = row
    return by_id


def norm_bool(v):
    if isinstance(v, bool):
        return v
    if v is None or v == "":
        return False
    return str(v).strip().lower() in ("true", "1", "yes", "checked")


def norm_multiselect(v):
    if not v:
        return set()
    if isinstance(v, list):
        return {str(x).strip() for x in v}
    return {x.strip() for x in str(v).split(",") if x.strip()}


def fetch_airtable():
    records = t.catalog_table.all()
    out = []
    for rec in records:
        fields = rec.get("fields") or {}
        pid = str(fields.get("Product ID") or "").strip()
        out.append({"record_id": rec.get("id"), "product_id": pid, "fields": fields})
    return out


def main():
    expected = load_csv_expected()
    airtable = fetch_airtable()
    by_id = {r["product_id"]: r for r in airtable if r["product_id"]}

    portal_live_ids = set(expected.keys())

    issues = []
    summary = {
        "airtable_row_count": len(airtable),
        "airtable_with_product_id": len(by_id),
        "expected_live_portal_count": len(portal_live_ids),
        "active_in_airtable": sum(
            1 for r in by_id.values() if norm_bool(r["fields"].get("Active"))
        ),
    }

    # Missing / extra
    missing_in_airtable = sorted(portal_live_ids - set(by_id.keys()))
    extra_in_airtable = sorted(set(by_id.keys()) - portal_live_ids)
    if missing_in_airtable:
        issues.append({"type": "missing_in_airtable", "product_ids": missing_in_airtable})
    if extra_in_airtable:
        issues.append({"type": "extra_in_airtable_not_in_live_portal", "product_ids": extra_in_airtable})

    compare_fields = [
        ("Product Name", "Product Name", "exact"),
        ("Active", "Active", "bool"),
        ("Use Timeslots", "Use Timeslots", "bool"),
        ("Is Refundable", "Is Refundable", "bool"),
        ("Provides Pricing", "Provides Pricing", "bool"),
        ("Cutoff Time", "Cutoff Time", "number"),
        ("Max Tickets", "Max Tickets", "number"),
        ("Required Order Data", "Required Order Data", "multiselect"),
        ("Required Visitor Data", "Required Visitor Data", "multiselect"),
        ("Adult Price", "Adult Price", "price"),
        ("Child Price", "Child Price", "price"),
        ("Currency", "Currency", "exact"),
        ("Daily Capacity", "Daily Capacity", "number"),
        ("Tickets Table Name", "Tickets Table Name", "exact"),
        ("Ticket View Name", "Ticket View Name", "exact"),
    ]

    per_product = []
    for pid in sorted(portal_live_ids):
        if pid not in by_id:
            per_product.append({"product_id": pid, "status": "MISSING"})
            continue
        fields = by_id[pid]["fields"]
        exp = expected[pid]
        diffs = []
        for csv_key, at_key, kind in compare_fields:
            ev = exp.get(csv_key, "")
            av = fields.get(at_key)
            if kind == "exact":
                es = str(ev).strip()
                as_ = "" if av is None else str(av).strip()
                if es != as_:
                    diffs.append({"field": at_key, "expected_csv": es, "airtable": as_})
            elif kind == "bool":
                if norm_bool(ev) != norm_bool(av):
                    diffs.append(
                        {
                            "field": at_key,
                            "expected_csv": norm_bool(ev),
                            "airtable": norm_bool(av),
                        }
                    )
            elif kind == "number":
                try:
                    en = float(ev) if str(ev).strip() else None
                except ValueError:
                    en = None
                try:
                    an = float(av) if av is not None and str(av).strip() != "" else None
                except (TypeError, ValueError):
                    an = None
                if en != an:
                    diffs.append({"field": at_key, "expected_csv": en, "airtable": an})
            elif kind == "price":
                try:
                    en = round(float(ev), 2) if str(ev).strip() else None
                except ValueError:
                    en = None
                try:
                    an = round(float(av), 2) if av is not None else None
                except (TypeError, ValueError):
                    an = None
                if en != an:
                    diffs.append({"field": at_key, "expected_csv": en, "airtable": an})
            elif kind == "multiselect":
                es = norm_multiselect(ev)
                as_ = norm_multiselect(av)
                if es != as_:
                    diffs.append(
                        {
                            "field": at_key,
                            "expected_csv": sorted(es),
                            "airtable": sorted(as_),
                        }
                    )

        # Portal name match (from CSV = portal snapshot)
        portal_name = exp.get("Product Name", "").strip()
        at_name = str(fields.get("Product Name") or "").strip()
        live_ok = norm_bool(fields.get("Active")) and pid in portal_live_ids

        per_product.append(
            {
                "product_id": pid,
                "portal_name": portal_name,
                "airtable_name": at_name,
                "name_matches_portal": portal_name == at_name,
                "active": norm_bool(fields.get("Active")),
                "diffs_from_import_csv": diffs,
                "status": "OK" if not diffs and portal_name == at_name else "MISMATCH",
            }
        )

    # Try API products list
    api_products = []
    try:
        import requests

        key = t.resolve_tiqets_api_key(t.load_tiqets_config())
        for base in ("http://127.0.0.1:5005",):
            try:
                r = requests.get(
                    f"{base}/v2/products",
                    headers={"API-Key": key},
                    timeout=15,
                )
                if r.status_code == 200:
                    api_products = r.json()
                    break
            except Exception:
                pass
    except Exception as exc:
        issues.append({"type": "api_fetch_error", "message": str(exc)})

    api_ids = {str(p.get("id")) for p in api_products}
    if api_products:
        issues.append(
            {
                "type": "api_active_ids",
                "count": len(api_ids),
                "ids": sorted(api_ids),
                "missing_from_api": sorted(portal_live_ids - api_ids),
                "extra_in_api": sorted(api_ids - portal_live_ids),
            }
        )

    payload = {
        "summary": summary,
        "issues": issues,
        "per_product": per_product,
        "airtable_snapshot": [
            {"product_id": r["product_id"], "fields": r["fields"]} for r in sorted(by_id.values(), key=lambda x: x["product_id"])
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"written": str(OUT), "summary": summary, "mismatch_count": sum(1 for p in per_product if p.get("status") == "MISMATCH")}, indent=2))


if __name__ == "__main__":
    main()
