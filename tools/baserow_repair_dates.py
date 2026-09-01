"""
One-time repair: re-push date fields from Airtable → Baserow (Africa/Cairo calendar day).

Usage (from OpenClaw_Version):
  python tools/baserow_repair_dates.py --dry-run
  python tools/baserow_repair_dates.py
  python tools/baserow_repair_dates.py --table List
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from baserow_sync import (  # noqa: E402
    AirtableBaserowSync,
    airtable_id_to_baserow_row_id,
    batch_update_rows_safe,
    build_row_payload,
    looks_like_date_only_field,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="List", help="Baserow/Airtable table name")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sync = AirtableBaserowSync()
    if not sync.enabled():
        print("Baserow sync disabled in config.json")
        return

    br = sync._br_client()
    patched_total = 0

    for target in sync.targets():
        tname = str(target.get("name") or "main")
        base_id = str(target.get("airtable_base_id") or "").strip()
        for table_name, tid in sync.resolve_target_tables(target):
            if args.table and table_name != args.table:
                continue
            at = sync._at_client(base_id)
            ck = sync._cache_key(tname, table_name)
            try:
                fields_meta, br_names, br_types, br_defs, id_field = sync._fields_for(
                    at, br, table_name, tid, ck
                )
            except RuntimeError as exc:
                print(f"skip {tname}/{table_name}: {exc}")
                continue
            if not id_field:
                print(f"skip {tname}/{table_name}: no Record ID field")
                continue

            type_by_name = {str(f.get("name") or ""): str(f.get("type") or "") for f in fields_meta}
            date_cols = []
            for n in sorted(br_names):
                at_t = type_by_name.get(n, "")
                br_d = br_defs.get(n)
                if br_types.get(n) == "date" or looks_like_date_only_field(n, at_t, br_d):
                    if at_t in ("date", "dateTime") or br_types.get(n) == "date":
                        date_cols.append(n)

            print(f"=== {tname}/{table_name} (tid={tid}) id_field={id_field}")
            print(f"    date columns: {date_cols}")
            if not date_cols:
                continue

            id_map = airtable_id_to_baserow_row_id(br, tid, id_field=id_field)
            print(f"    baserow rows indexed: {len(id_map)}")

            records = at.fetch_records(table_name)
            scanned = 0
            batch: list = []
            for rec in records:
                scanned += 1
                aid = str(rec.get("id") or "")
                brow = id_map.get(aid)
                if not brow:
                    continue
                payload = build_row_payload(
                    rec,
                    fields_meta,
                    br_names,
                    br_field_types=br_types,
                    br_field_defs=br_defs,
                    include_airtable_id=False,
                    id_field=id_field,
                )
                patch = {k: payload[k] for k in date_cols if k in payload}
                if not patch:
                    continue
                batch.append({"id": brow, **patch})
                if len(batch) >= 40:
                    if args.dry_run:
                        print(f"    dry-run sample: {batch[0]}")
                        print(f"    dry-run would patch batch of {len(batch)}")
                    else:
                        ok, skipped = batch_update_rows_safe(br, tid, batch)
                        patched_total += ok
                        print(f"    patched +{ok} (skipped {skipped}), total={patched_total}")
                    batch = []

            if batch:
                if args.dry_run:
                    print(f"    dry-run sample: {batch[0]}")
                    print(f"    dry-run would patch batch of {len(batch)}")
                else:
                    ok, skipped = batch_update_rows_safe(br, tid, batch)
                    patched_total += ok
                    print(f"    patched +{ok} (skipped {skipped}), total={patched_total}")
            print(f"    scanned airtable records: {scanned}")

    print(f"Done. date-patched rows={patched_total} dry_run={args.dry_run}")


if __name__ == "__main__":
    main()
