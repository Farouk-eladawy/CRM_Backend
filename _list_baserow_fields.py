# -*- coding: utf-8 -*-
"""List Baserow field names for List + استفسارات جديدة tables."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd()
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import BaserowApi, load_config


def resolve_table(br, database_id, preferred_name, fallback_id=None):
    tables = br.list_tables(database_id)
    by_name = {str(t.get("name") or ""): t for t in tables}
    if preferred_name in by_name:
        return by_name[preferred_name]
    if fallback_id is not None:
        for t in tables:
            if int(t.get("id") or 0) == int(fallback_id):
                return t
    # fuzzy: contains preferred
    for name, t in by_name.items():
        if preferred_name and preferred_name in name:
            return t
    return None


def analyze(label, fields):
    names = [str(f.get("name") or "") for f in fields]
    has_upsert = "airtable_record_id" in names
    matches = [n for n in names if "airtable" in n.lower() or "record" in n.lower()]
    print("=" * 60)
    print(label)
    print(f"total_fields={len(names)}")
    print(f'upsert_key_airtable_record_id_exists={has_upsert}')
    print(f"names_containing_airtable_or_record={matches}")
    print("first_40_field_names:")
    for i, n in enumerate(names[:40], 1):
        print(f"  {i:2d}. {n}")
    return names, has_upsert, matches


def main():
    cfg = load_config()
    br_cfg = cfg.get("baserow") or {}
    br = BaserowApi.from_config(br_cfg)

    targets = [
        ("database 5 / List", 5, "List", 21),
        ("database 3 / استفسارات جديدة", 3, "استفسارات جديدة", 11),
    ]

    results = {}
    for label, db_id, tname, tid in targets:
        print(f"\n--- Resolving {label} ---")
        try:
            table = resolve_table(br, db_id, tname, tid)
        except Exception as e:
            print(f"ERROR listing tables for db {db_id}: {e}")
            results[label] = {"error": str(e)}
            continue
        if not table:
            print(f"Table not found: name={tname!r} id={tid} in database {db_id}")
            # dump available names
            try:
                avail = [(t.get("id"), t.get("name")) for t in br.list_tables(db_id)]
                print(f"available tables: {avail}")
            except Exception as e2:
                print(f"could not list: {e2}")
            results[label] = {"error": "not found"}
            continue
        print(f"resolved table id={table.get('id')} name={table.get('name')!r}")
        fields = br.list_fields(int(table["id"]))
        names, has_upsert, matches = analyze(
            f"{label} (id={table.get('id')}, name={table.get('name')!r})", fields
        )
        results[label] = {
            "table_id": table.get("id"),
            "table_name": table.get("name"),
            "field_names": names,
            "airtable_record_id_exists": has_upsert,
            "airtable_or_record_matches": matches,
        }

    out = ROOT / "_baserow_field_names_check.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
