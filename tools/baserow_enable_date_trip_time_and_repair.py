"""
Re-enable Date Trip time in Baserow (Africa/Cairo) and re-push values from Airtable.

Usage:
  python tools/baserow_enable_date_trip_time_and_repair.py
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
)
from tools.migrate_airtable_to_baserow import BaserowApi, load_config  # noqa: E402

# Fields that must keep date+time, forced to Africa/Cairo
WITH_TIME_NAMES = {
    "Date Trip",
    "Real Date Trip",
}


def enable_time_on_fields(br: BaserowApi, table_id: int, dry_run: bool) -> list:
    changed = []
    for f in br.list_fields(table_id):
        name = str(f.get("name") or "")
        if f.get("type") != "date" or name not in WITH_TIME_NAMES:
            continue
        body = {
            "date_include_time": True,
            "date_force_timezone": "Africa/Cairo",
            "date_show_tzinfo": True,
            "date_time_format": "24",
        }
        print(
            f"  PATCH {name!r} id={f.get('id')}: include_time=True tz=Africa/Cairo "
            f"(was include_time={f.get('date_include_time')})"
        )
        if not dry_run:
            br.update_field(int(f["id"]), body)
        changed.append(name)
    return changed


def repair_date_trip(sync: AirtableBaserowSync, table_name: str, dry_run: bool) -> int:
    br = sync._br_client()
    sync._field_cache = {}
    patched = 0
    for target in sync.targets():
        tname = str(target.get("name") or "main")
        base_id = str(target.get("airtable_base_id") or "").strip()
        for tname_br, tid in sync.resolve_target_tables(target):
            if tname_br != table_name:
                continue
            at = sync._at_client(base_id)
            ck = sync._cache_key(tname, table_name)
            fields_meta, br_names, br_types, br_defs, id_field = sync._fields_for(
                at, br, table_name, tid, ck
            )
            if not id_field:
                print("no Record ID — abort")
                return 0
            cols = [n for n in WITH_TIME_NAMES if n in br_names]
            # also other date fields so Create Date etc stay consistent
            for n, t in br_types.items():
                if t == "date" and n not in cols:
                    cols.append(n)
            print(f"=== repair {table_name} tid={tid} cols={cols}")
            print(f"    Date Trip br options: { {k: br_defs.get('Date Trip', {}).get(k) for k in ('date_include_time','date_force_timezone')} }")
            id_map = airtable_id_to_baserow_row_id(br, tid, id_field=id_field)
            records = at.fetch_records(table_name)
            batch = []
            sample_printed = 0
            for rec in records:
                brow = id_map.get(str(rec.get("id") or ""))
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
                patch = {k: payload[k] for k in cols if k in payload}
                if not patch:
                    continue
                if sample_printed < 3 and "Date Trip" in patch:
                    at_raw = (rec.get("fields") or {}).get("Date Trip")
                    print(f"    sample AT={at_raw!r} -> BR={patch.get('Date Trip')!r}")
                    sample_printed += 1
                batch.append({"id": brow, **patch})
                if len(batch) >= 40:
                    if dry_run:
                        print(f"    dry-run batch {len(batch)} sample={batch[0]}")
                    else:
                        ok, skipped = batch_update_rows_safe(br, tid, batch)
                        patched += ok
                        if patched % 400 == 0 or ok:
                            print(f"    patched total={patched} (+{ok} skip={skipped})")
                    batch = []
            if batch:
                if dry_run:
                    print(f"    dry-run batch {len(batch)} sample={batch[0]}")
                else:
                    ok, skipped = batch_update_rows_safe(br, tid, batch)
                    patched += ok
                    print(f"    patched total={patched} (+{ok} skip={skipped})")
    return patched


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="List")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    br = BaserowApi.from_config(cfg.get("baserow") or {})
    sync = AirtableBaserowSync(cfg)

    for target in sync.targets():
        for table_name, tid in sync.resolve_target_tables(target):
            if table_name != args.table:
                continue
            print(f"Enable time on Date Trip fields ({table_name} tid={tid})...")
            changed = enable_time_on_fields(br, tid, args.dry_run)
            print(f"  updated: {changed}")

    print("Re-push dates with Cairo time...")
    n = repair_date_trip(sync, args.table, args.dry_run)
    print(f"Done. patched_rows={n} dry_run={args.dry_run}")


if __name__ == "__main__":
    main()
