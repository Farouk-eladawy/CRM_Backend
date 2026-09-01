# -*- coding: utf-8 -*-
"""Baseline incremental sync after manual Baserow Import from Airtable."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from baserow_sync import (  # noqa: E402
    AirtableBaserowSync,
    load_sync_state,
    save_sync_state,
    set_sync_paused,
    resolve_id_field_name,
)
from tools.migrate_airtable_to_baserow import BaserowApi, load_config  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def main() -> int:
    cfg = load_config()
    syncer = AirtableBaserowSync(cfg)
    br = BaserowApi.from_config(cfg["baserow"])
    preferred = syncer.preferred_id_field()
    now = utc_now()
    state = load_sync_state()
    tables_state = state.setdefault("tables", {})
    ready = []
    skipped = []

    for target in syncer.targets():
        tname = str(target.get("name") or "main")
        pairs = syncer.resolve_target_tables(target)
        for table_name, tid in pairs:
            fields = {str(f.get("name") or "") for f in br.list_fields(tid)}
            id_field = resolve_id_field_name(fields, preferred)
            key = f"{tname}::{table_name}"
            if not id_field:
                skipped.append({"table": table_name, "id": tid, "reason": f"missing {preferred}"})
                continue
            tables_state[key] = {
                "baserow_table_id": tid,
                "id_field": id_field,
                "last_modified_cursor": now,
                "last_run": now,
                "last_result": "baseline_after_manual_import",
                "last_created": 0,
                "last_updated": 0,
            }
            ready.append({"table": table_name, "id": tid, "id_field": id_field})

    state["tables"] = tables_state
    state["paused"] = False
    state["pause_reason"] = ""
    state["pause_updated_at"] = now
    state["baseline_at"] = now
    state["note"] = "Incremental Airtable→Baserow from baseline; only tables with Record ID"
    save_sync_state(state)

    out = {"baseline_at": now, "ready": ready, "skipped_no_record_id": skipped}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    path = ROOT / "tools" / "_baserow_sync_baseline.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nUnpaused. Ready tables: {len(ready)} | skipped: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
