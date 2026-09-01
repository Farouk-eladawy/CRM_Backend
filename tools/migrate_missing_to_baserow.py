# -*- coding: utf-8 -*-
"""Migrate Airtable tables that are missing from Baserow (main + religious)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import (  # noqa: E402
    AirtableSource,
    BaserowApi,
    load_config,
    migrate_table,
    load_state,
    save_state,
)

EXCLUDE = {
    "Tito Sunny",
    "Nile_Crystal_Booking",
    "Fun_Time_Booking",
    "Nile_GYG_Analytics",
    "Airtable import report",
}

SKIP_SUBSTRINGS = ("import report",)


def skip_name(name: str) -> bool:
    if name in EXCLUDE:
        return True
    low = name.lower()
    return any(s in low for s in SKIP_SUBSTRINGS)


def main() -> int:
    cfg = load_config()
    br_cfg = cfg["baserow"]
    at_cfg = cfg["airtable"]
    br = BaserowApi.from_config(br_cfg)

    targets = [
        {
            "name": "main",
            "database_id": int(br_cfg.get("database_id") or 5),
            "airtable_base_id": str(at_cfg.get("base_id") or ""),
        },
        {
            "name": "religious",
            "database_id": int(br_cfg.get("religious_database_id") or 3),
            "airtable_base_id": str(at_cfg.get("religious_base_id") or ""),
        },
    ]

    state = load_state()
    state.setdefault("tables", {})
    plan = []

    for t in targets:
        base_id = t["airtable_base_id"]
        db_id = t["database_id"]
        cfg_at = dict(cfg)
        cfg_at["airtable"] = {**at_cfg, "base_id": base_id}
        at = AirtableSource(cfg_at)
        at_names = [x["name"] for x in at.fetch_schema()]
        br_names = {str(x.get("name") or "") for x in br.list_tables(db_id)}
        missing = [n for n in at_names if n not in br_names and not skip_name(n)]
        plan.append(
            {
                "target": t["name"],
                "database_id": db_id,
                "existing": sorted(br_names),
                "missing": missing,
                "excluded_present": [n for n in at_names if n in EXCLUDE],
            }
        )

    out_path = ROOT / "tools" / "_migrate_missing_plan.json"
    out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PLAN written to", out_path)
    for p in plan:
        print(f"\n[{p['target']}] db={p['database_id']} missing={len(p['missing'])}")
        for n in p["missing"]:
            print("  -", n)

    # Migrate
    for t, p in zip(targets, plan):
        if not p["missing"]:
            continue
        base_id = t["airtable_base_id"]
        db_id = t["database_id"]
        cfg_at = dict(cfg)
        cfg_at["airtable"] = {**at_cfg, "base_id": base_id}
        at = AirtableSource(cfg_at)
        id_by_name = {x["name"]: str(x["id"]) for x in at.fetch_schema()}
        link_table_ids = {}
        # Seed link map with existing baserow tables that share airtable ids from state / live
        for bt in br.list_tables(db_id):
            bname = str(bt.get("name") or "")
            tid = int(bt.get("id") or 0)
            at_id = id_by_name.get(bname)
            if at_id and tid:
                link_table_ids[at_id] = tid

        # Prefer tables with fewer link fields first
        def link_count(name: str) -> int:
            tbl = at.table_by_name(name)
            return sum(1 for f in tbl.get("fields") or [] if f.get("type") == "multipleRecordLinks")

        names = sorted(p["missing"], key=link_count)
        print(f"\n== Migrating {t['name']} ({len(names)} tables) ==")
        for name in names:
            print(f"\n== {name} ==")
            try:
                info = migrate_table(
                    br,
                    at,
                    db_id,
                    name,
                    max_records=0,
                    skip_existing=True,
                    recreate=False,
                    state=state,
                    link_table_ids=link_table_ids,
                )
                info["airtable_table_id"] = id_by_name.get(name)
                info["baserow_database_id"] = db_id
                info["sync_target"] = t["name"]
                state["tables"][f"{t['name']}::{name}"] = info
                # also keep plain name for main List compatibility
                if t["name"] == "main":
                    state["tables"][name] = info
                save_state(state)
                print(f"  done {name}: synced={info.get('records_synced')} complete={info.get('complete')}")
            except Exception as exc:
                print(f"  FAILED {name}: {exc}")
                save_state(state)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
