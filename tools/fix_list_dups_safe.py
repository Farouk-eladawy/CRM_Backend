"""
Fix List duplicate fields safely (single sample pass):
  - For each "Foo" + "Foo (2)": keep denser column under clean name "Foo".
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import (  # noqa: E402
    AUTO_COMPUTED_TYPES,
    BaserowApi,
    load_config,
    load_state,
)
import requests

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
    raise RuntimeError("Airtable List not found")


def sample_fills(br: BaserowApi, table_id: int, pages: int = 5) -> dict[str, int]:
    fills: dict[str, int] = defaultdict(int)
    for page in range(1, pages + 1):
        data = br._req(
            "GET",
            f"/api/database/rows/table/{table_id}/",
            params={"user_field_names": "true", "size": 200, "page": page},
        )
        for row in data.get("results") or []:
            for k, v in row.items():
                if k in ("id", "order") or k.startswith("field_"):
                    continue
                if v is None or v == "" or v == []:
                    continue
                fills[k] += 1
        if not data.get("next"):
            break
        time.sleep(0.05)
    return dict(fills)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    br = BaserowApi.from_config(cfg["baserow"])
    state = load_state()
    tid = int((state.get("tables") or {}).get("List", {}).get("baserow_table_id") or 15)

    fields = br.list_fields(tid)
    by_name = {str(f.get("name") or ""): f for f in fields}

    pairs: list[tuple[str, str]] = []
    for name in list(by_name):
        m = DUP_RE.match(name)
        if m and m.group(1) in by_name:
            pairs.append((m.group(1), name))

    print(f"table_id={tid} fields={len(fields)} dup_pairs={len(pairs)}")
    print("Sampling row fills (up to 1000 rows)...")
    fills = sample_fills(br, tid, pages=5)

    actions = []
    keep_dup = 0
    for base, dup in pairs:
        c_base = fills.get(base, 0)
        c_dup = fills.get(dup, 0)
        prefer = "dup" if c_dup > c_base else "base"
        if prefer == "dup":
            keep_dup += 1
        actions.append((prefer, base, dup, c_base, c_dup))
        print(f"  {base!r}: base={c_base} dup={c_dup} -> KEEP_{prefer.upper()}")

    print(f"\nPairs: {len(actions)} (prefer denser dup: {keep_dup})")

    # Missing with strip normalize
    covered = set()
    for n in by_name:
        covered.add(n)
        covered.add(n.strip())
        m = DUP_RE.match(n)
        if m:
            covered.add(m.group(1))
            covered.add(m.group(1).strip())

    print("\nMISSING after strip-normalize:")
    real_missing = []
    whitespace_only = []
    computed = []
    for f in airtable_list_fields(cfg):
        n = str(f.get("name") or "")
        if f.get("type") in AUTO_COMPUTED_TYPES:
            computed.append(n)
            continue
        if not n or n == "Name":
            continue
        if n in covered or n.strip() in covered:
            if n != n.strip() and n not in by_name:
                whitespace_only.append(n)
            continue
        real_missing.append((f.get("type"), n))
        print(f"  REAL_MISSING  {f.get('type')}  {n!r}")
    if not real_missing:
        print("  (none — all manual Airtable fields covered)")
    print(f"Computed skipped by design: {len(computed)}")
    if whitespace_only:
        print("Whitespace-only Airtable names (twin already exists):")
        for n in whitespace_only:
            print(f"  WS  {n!r}")

    if not args.apply:
        print("\nDry run only. Pass --apply to delete/rename duplicates.")
        return 0

    deleted = 0
    for prefer, base, dup, c_base, c_dup in actions:
        base_f = by_name.get(base)
        dup_f = by_name.get(dup)
        if not base_f or not dup_f:
            continue
        try:
            if prefer == "base":
                print(f"DELETE {dup!r} id={dup_f['id']}")
                br._req("DELETE", f"/api/database/fields/{int(dup_f['id'])}/")
                by_name.pop(dup, None)
            else:
                tmp = f"{base} __old_dup"
                # ensure tmp free
                while tmp in by_name:
                    tmp += "_"
                print(f"SWAP keep {dup!r} as {base!r} (delete old {base!r})")
                br._req("PATCH", f"/api/database/fields/{int(base_f['id'])}/", json={"name": tmp})
                time.sleep(0.12)
                br._req("PATCH", f"/api/database/fields/{int(dup_f['id'])}/", json={"name": base})
                time.sleep(0.12)
                br._req("DELETE", f"/api/database/fields/{int(base_f['id'])}/")
                by_name.pop(dup, None)
                by_name[base] = dup_f
            deleted += 1
            time.sleep(0.18)
        except RuntimeError as exc:
            print(f"  FAIL {base}/{dup}: {exc}")

    print(f"\nDone. Fixed {deleted} duplicate pairs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
