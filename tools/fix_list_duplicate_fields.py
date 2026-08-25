"""
Audit + fix List fields in Baserow vs Airtable:
  1) Report duplicates (Name (2)), missing, skipped-computed
  2) --fix: delete duplicate fields only when base name also exists
  3) --rename-orphans: rename "Foo (2)" -> "Foo" when Foo does not exist
  4) --add-missing: create missing non-computed Airtable fields as text
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import (  # noqa: E402
    AUTO_COMPUTED_TYPES,
    BaserowApi,
    load_config,
    load_state,
    unique_field_name,
)

DUP_RE = re.compile(r"^(.*) \((\d+)\)$")


def airtable_list_fields(cfg: dict) -> list[dict]:
    at = cfg["airtable"]
    r = requests.get(
        f"https://api.airtable.com/v0/meta/bases/{at['base_id']}/tables",
        headers={"Authorization": f"Bearer {at['api_key']}"},
        timeout=60,
    )
    r.raise_for_status()
    for t in r.json().get("tables") or []:
        if t.get("name") == "List":
            return list(t.get("fields") or [])
    raise RuntimeError("Airtable List table not found")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="Delete true duplicates")
    ap.add_argument("--rename-orphans", action="store_true", help="Rename Foo (2) -> Foo if Foo missing")
    ap.add_argument("--add-missing", action="store_true", help="Add missing Airtable fields as text")
    ap.add_argument("--dry-run", action="store_true", help="Print only, no changes")
    args = ap.parse_args()

    cfg = load_config()
    br = BaserowApi.from_config(cfg["baserow"])
    state = load_state()
    tid = int((state.get("tables") or {}).get("List", {}).get("baserow_table_id") or 0)
    if not tid:
        # fallback: find by name
        db = int(cfg["baserow"].get("database_id") or 1)
        t = br.find_table_by_name(db, "List")
        if not t:
            print("List table not found in Baserow", file=sys.stderr)
            return 2
        tid = int(t["id"])

    fields = br.list_fields(tid)
    by_name = {str(f.get("name") or ""): f for f in fields}
    names = list(by_name.keys())

    # --- duplicates ---
    dups_to_delete: list[dict] = []
    orphans: list[dict] = []
    for f in fields:
        name = str(f.get("name") or "")
        m = DUP_RE.match(name)
        if not m:
            continue
        base, num = m.group(1), int(m.group(2))
        if base in by_name:
            dups_to_delete.append(f)
        else:
            orphans.append(f)

    at_fields = airtable_list_fields(cfg)
    at_manual = [f for f in at_fields if f.get("type") not in AUTO_COMPUTED_TYPES]
    at_computed = [f for f in at_fields if f.get("type") in AUTO_COMPUTED_TYPES]

    # Normalize: treat "Foo (2)" as covering "Foo" for presence check
    covered: set[str] = set()
    for n in names:
        covered.add(n)
        m = DUP_RE.match(n)
        if m:
            covered.add(m.group(1))

    missing = []
    for f in at_manual:
        n = str(f.get("name") or "")
        if n and n not in covered and n != "Name":
            missing.append(f)

    print(f"Baserow List table_id={tid}")
    print(f"Baserow fields: {len(fields)}")
    print(f"Airtable fields: {len(at_fields)} (manual {len(at_manual)}, computed-skipped {len(at_computed)})")
    print()
    print(f"DUPLICATES (base also exists) — delete candidates: {len(dups_to_delete)}")
    for f in sorted(dups_to_delete, key=lambda x: x.get("name") or ""):
        print(f"  DEL  id={f.get('id')}  {f.get('name')}")
    print()
    print(f"ORPHAN duplicates (no base name) — rename candidates: {len(orphans)}")
    for f in sorted(orphans, key=lambda x: x.get("name") or ""):
        m = DUP_RE.match(str(f.get("name") or ""))
        print(f"  REN  id={f.get('id')}  {f.get('name')}  ->  {m.group(1) if m else '?'}")
    print()
    print(f"MISSING (Airtable manual not in Baserow): {len(missing)}")
    for f in missing:
        print(f"  ADD  {f.get('type'):<22} {f.get('name')}")
    print()
    print(f"SKIPPED computed (by design): {len(at_computed)}")
    for f in at_computed:
        print(f"  ---  {f.get('type'):<22} {f.get('name')}")

    if args.dry_run or not (args.fix or args.rename_orphans or args.add_missing):
        print("\n(dry report only — pass --fix / --rename-orphans / --add-missing to apply)")
        return 0

    if args.fix:
        for f in dups_to_delete:
            fid = int(f["id"])
            name = f.get("name")
            print(f"deleting field {name} id={fid}...")
            if not args.dry_run:
                br._req("DELETE", f"/api/database/fields/{fid}/")
                time.sleep(0.15)
        print(f"deleted {len(dups_to_delete)} duplicate fields")

    if args.rename_orphans:
        used = {str(x.get("name") or "") for x in br.list_fields(tid)}
        for f in orphans:
            old = str(f.get("name") or "")
            m = DUP_RE.match(old)
            if not m:
                continue
            new = m.group(1)
            if new in used:
                new = unique_field_name(new, used)
            print(f"renaming {old!r} -> {new!r} id={f.get('id')}...")
            if not args.dry_run:
                br._req(
                    "PATCH",
                    f"/api/database/fields/{int(f['id'])}/",
                    json={"name": new},
                )
                used.discard(old)
                used.add(new)
                time.sleep(0.15)

    if args.add_missing:
        used = {str(x.get("name") or "") for x in br.list_fields(tid)}
        for f in missing:
            name = unique_field_name(str(f.get("name") or "Field"), used)
            body = {"name": name, "type": "text"}
            print(f"adding missing field {name} (as text, was {f.get('type')})...")
            if not args.dry_run:
                try:
                    br.create_field(tid, body)
                    used.add(name)
                    time.sleep(0.1)
                except RuntimeError as exc:
                    print(f"  skip: {exc}")

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
