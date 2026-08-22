"""
Export Airtable List table to CSV for NocoDB import (first migration step).

Usage (from OpenClaw_Version folder):
  python tools/export_airtable_list_for_nocodb.py
  python tools/export_airtable_list_for_nocodb.py --max 500 --out exports/list_for_nocodb.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from airtable_fields import FieldIds, ID_TO_READABLE_NAME, TABLE_NAME  # noqa: E402


def load_config() -> dict:
    cfg_path = ROOT / "config.json"
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f)


def field_label(field_id: str) -> str:
    return ID_TO_READABLE_NAME.get(field_id, field_id)


def flatten_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(x) for x in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Airtable List to CSV for NocoDB")
    parser.add_argument("--max", type=int, default=0, help="Max records (0 = all)")
    parser.add_argument("--out", default="exports/list_for_nocodb.csv")
    args = parser.parse_args()

    cfg = load_config()
    at = cfg.get("airtable") or {}
    api_key = str(at.get("api_key") or "").strip()
    base_id = str(at.get("base_id") or "").strip()
    if not api_key or not base_id:
        print("Missing airtable.api_key or base_id in config.json", file=sys.stderr)
        return 2

    from pyairtable import Api

    api = Api(api_key)
    table = api.table(base_id, TABLE_NAME)
    kwargs = {}
    if args.max and args.max > 0:
        kwargs["max_records"] = args.max
    records = table.all(**kwargs)

    # Collect all field ids present
    field_ids: set[str] = set()
    for rec in records:
        field_ids.update((rec.get("fields") or {}).keys())

    preferred = [
        FieldIds.BOOKING_NR,
        FieldIds.DATE_TRIP,
        FieldIds.AGENCY,
        FieldIds.TRIP_NAME,
        FieldIds.CUSTOMER_NAME,
        FieldIds.CUSTOMER_PHONE,
        FieldIds.CUSTOMER_EMAIL,
        FieldIds.HOTEL_NAME,
        FieldIds.PICKUP_TIME,
        FieldIds.BOOKING_STATUS,
        FieldIds.CAR_TYPE,
        FieldIds.LOCAL_DRIVER,
        FieldIds.ADT,
        FieldIds.CHD,
        FieldIds.INF,
        FieldIds.DES,
        FieldIds.OPTION,
    ]
    ordered = [fid for fid in preferred if fid in field_ids]
    ordered += sorted(fid for fid in field_ids if fid not in ordered)

    headers = ["airtable_record_id"] + [field_label(fid) for fid in ordered]
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for rec in records:
            fields = rec.get("fields") or {}
            row = [rec.get("id", "")]
            for fid in ordered:
                row.append(flatten_value(fields.get(fid)))
            writer.writerow(row)

    print(f"Exported {len(records)} rows -> {out_path}")
    print("Import in NocoDB: Base FTS Bookings -> Import -> CSV")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
