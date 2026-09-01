# -*- coding: utf-8 -*-
"""Inspect Baserow List table date/time-related fields and sample values."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import BaserowApi, load_config

KEYWORDS = ("date", "time", "create", "modified", "trip", "pickup")
SAMPLE_FIELD_HINTS = ("Date Trip", "Create Date", "Create Date  ", "pickup time")
DATE_OPTION_KEYS = (
    "date_include_time",
    "date_force_timezone",
    "date_format",
    "date_time_format",
    "date_show_tzinfo",
    "timezone",
    "date_force_timezone_offset",
)


def name_matches(name: str) -> bool:
    low = (name or "").lower()
    return any(k in low for k in KEYWORDS)


def pick_sample_fields(fields):
    wanted = []
    for hint in SAMPLE_FIELD_HINTS:
        for f in fields:
            n = str(f.get("name") or "")
            if n == hint or n.strip() == hint.strip() or n.lower() == hint.lower():
                if n not in wanted:
                    wanted.append(n)
    # also fuzzy pickup time
    for f in fields:
        n = str(f.get("name") or "")
        if "pickup" in n.lower() and "time" in n.lower() and n not in wanted:
            wanted.append(n)
    return wanted


def extract_field_info(f: dict) -> dict:
    name = str(f.get("name") or "")
    ftype = str(f.get("type") or "")
    info = {"name": name, "type": ftype, "id": f.get("id")}
    options = {}
    for k in DATE_OPTION_KEYS:
        if k in f:
            options[k] = f[k]
    # also capture any other keys starting with date_
    for k, v in f.items():
        if k.startswith("date_") and k not in options:
            options[k] = v
    if options:
        info["date_options"] = options
    return info


def main():
    cfg = load_config()
    br_cfg = cfg.get("baserow") or {}
    br = BaserowApi.from_config(br_cfg)

    database_id = int(br_cfg.get("database_id") or 0)
    list_table_id = br_cfg.get("list_table_id")

    table = None
    if list_table_id:
        tid = int(list_table_id)
        # verify exists
        for t in br.list_tables(database_id):
            if int(t.get("id") or 0) == tid:
                table = t
                break
        if table is None:
            table = {"id": tid, "name": "List (from config id)"}
    if table is None:
        for t in br.list_tables(database_id):
            if str(t.get("name") or "") == "List":
                table = t
                break
    if table is None:
        raise SystemExit(f"List table not found in database_id={database_id}")

    table_id = int(table["id"])
    fields = br.list_fields(table_id)

    matched = [extract_field_info(f) for f in fields if name_matches(str(f.get("name") or ""))]

    sample_names = pick_sample_fields(fields)
    # fetch 3 rows
    rows_data = br._req(
        "GET",
        f"/api/database/rows/table/{table_id}/",
        params={"user_field_names": "true", "size": 3},
    )
    rows = list(rows_data.get("results") or rows_data) if isinstance(rows_data, dict) else list(rows_data or [])

    samples = []
    for row in rows[:3]:
        entry = {"id": row.get("id")}
        for fn in sample_names:
            entry[fn] = row.get(fn)
        samples.append(entry)

    # summary types for Date Trip and date-like
    type_by_name = {m["name"]: m["type"] for m in matched}
    date_trip_type = None
    for m in matched:
        if m["name"].strip().lower() == "date trip":
            date_trip_type = m["type"]
            break

    out = {
        "database_id": database_id,
        "table_id": table_id,
        "table_name": table.get("name"),
        "matched_fields": matched,
        "sample_field_names": sample_names,
        "sample_rows": samples,
        "date_trip_type": date_trip_type,
        "type_by_name": type_by_name,
    }

    out_path = Path(__file__).resolve().parent / "_baserow_date_fields_check.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print("=== Baserow List date-like fields ===")
    print(f"database_id={database_id} table_id={table_id} name={table.get('name')!r}")
    print(f"matched_count={len(matched)}")
    for m in matched:
        opts = m.get("date_options") or {}
        opt_s = ", ".join(f"{k}={v!r}" for k, v in opts.items()) if opts else "(no date_* options)"
        print(f"  - {m['name']!r} type={m['type']} | {opt_s}")
    print("\n=== Sample rows (raw) ===")
    for s in samples:
        print(json.dumps(s, ensure_ascii=False, default=str))
    print("\n=== Summary ===")
    print(f"Date Trip type: {date_trip_type}")
    print("Other date-like field types:")
    for name, typ in sorted(type_by_name.items()):
        print(f"  {name!r}: {typ}")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
