"""
1) Set calendar-day Baserow fields to date_include_time=False (fixes Date Trip TZ shift).
2) Re-push date values from Airtable → Baserow (Cairo-safe).

Usage:
  python tools/baserow_fix_date_fields_and_repair.py
  python tools/baserow_fix_date_fields_and_repair.py --dry-run
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
from tools.migrate_airtable_to_baserow import BaserowApi, load_config  # noqa: E402

# Force date-only (no time) — NOT Date Trip / Real Date Trip (those keep Cairo time).
FORCE_DATE_ONLY_NAMES = {
    "Review Date",
    "Issue Tickets Date",
}


def fix_field_settings(br: BaserowApi, table_id: int, dry_run: bool) -> list:
    changed = []
    for f in br.list_fields(table_id):
        name = str(f.get("name") or "")
        if f.get("type") != "date":
            continue
        if name not in FORCE_DATE_ONLY_NAMES:
            continue
        if not f.get("date_include_time"):
            print(f"  OK already date-only: {name!r} (id={f.get('id')})")
            continue
        body = {
            "date_include_time": False,
            "date_show_tzinfo": False,
        }
        # Keep Cairo as force tz null for pure dates (Baserow date-only ignores clock)
        print(f"  PATCH {name!r} id={f.get('id')}: date_include_time False")
        if not dry_run:
            br.update_field(int(f["id"]), body)
        changed.append(name)
    return changed


def repair_dates(sync: AirtableBaserowSync, table_filter: str, dry_run: bool) -> int:
    br = sync._br_client()
    patched_total = 0
    # Clear field cache so we see updated date_include_time
    sync._field_cache = {}

    for target in sync.targets():
        tname = str(target.get("name") or "main")
        base_id = str(target.get("airtable_base_id") or "").strip()
        for table_name, tid in sync.resolve_target_tables(target):
            if table_filter and table_name != table_filter:
                continue
            at = sync._at_client(base_id)
            ck = sync._cache_key(tname, table_name)
            fields_meta, br_names, br_types, br_defs, id_field = sync._fields_for(
                at, br, table_name, tid, ck
            )
            if not id_field:
                print(f"skip {table_name}: no Record ID")
                continue

            type_by_name = {str(f.get("name") or ""): str(f.get("type") or "") for f in fields_meta}
            date_cols = []
            for n in sorted(br_names):
                at_t = type_by_name.get(n, "")
                br_d = br_defs.get(n)
                if br_types.get(n) != "date" and not looks_like_date_only_field(n, at_t, br_d):
                    continue
                if at_t in ("date", "dateTime", "createdTime", "lastModifiedTime") or br_types.get(n) == "date":
                    date_cols.append(n)

            print(f"=== repair {tname}/{table_name} tid={tid}")
            print(f"    date columns: {date_cols}")
            id_map = airtable_id_to_baserow_row_id(br, tid, id_field=id_field)
            print(f"    indexed rows: {len(id_map)}")

            records = at.fetch_records(table_name)
            batch: list = []
            scanned = 0
            for rec in records:
                scanned += 1
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
                patch = {k: payload[k] for k in date_cols if k in payload}
                if not patch:
                    continue
                batch.append({"id": brow, **patch})
                if len(batch) >= 40:
                    if dry_run:
                        print(f"    dry-run sample: {batch[0]}")
                        print(f"    dry-run batch size {len(batch)}")
                    else:
                        ok, skipped = batch_update_rows_safe(br, tid, batch)
                        patched_total += ok
                        print(f"    patched +{ok} skip={skipped} total={patched_total}")
                    batch = []
            if batch:
                if dry_run:
                    print(f"    dry-run sample: {batch[0]}")
                    print(f"    dry-run batch size {len(batch)}")
                else:
                    ok, skipped = batch_update_rows_safe(br, tid, batch)
                    patched_total += ok
                    print(f"    patched +{ok} skip={skipped} total={patched_total}")
            print(f"    scanned={scanned}")
    return patched_total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="List")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-field-fix", action="store_true")
    ap.add_argument("--skip-repair", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    br = BaserowApi.from_config(cfg.get("baserow") or {})
    sync = AirtableBaserowSync(cfg)

    # Resolve List table id
    for target in sync.targets():
        for table_name, tid in sync.resolve_target_tables(target):
            if table_name != args.table:
                continue
            print(f"Fix field settings on {table_name} (tid={tid})...")
            if not args.skip_field_fix:
                changed = fix_field_settings(br, tid, args.dry_run)
                print(f"  fields updated: {changed or '(none)'}")

    if not args.skip_repair:
        print("Re-push dates from Airtable...")
        n = repair_dates(sync, args.table, args.dry_run)
        print(f"Done. patched_rows={n} dry_run={args.dry_run}")
    else:
        print("Skipped repair.")


if __name__ == "__main__":
    main()
