"""Print tables in the List migration bundle."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import (  # noqa: E402
    AirtableSource,
    discover_list_link_targets,
    load_config,
    load_state,
)

cfg = load_config()
at = AirtableSource(cfg)
deps = discover_list_link_targets(at)
bundle = deps + (["List"] if "List" not in deps else [])
state = load_state().get("tables") or {}

print("LIST BUNDLE TABLES:")
for name in bundle:
    info = state.get(name) or {}
    status = "complete" if info.get("complete") else (
        f"partial({info.get('records_synced', 0)})" if info else "pending"
    )
    print(f"  {name}: {status}")

print("\nLINK FIELDS IN LIST:")
tbl = at.table_by_name("List")
for f in tbl.get("fields") or []:
    if f.get("type") == "multipleRecordLinks":
        print(f"  - {f.get('name')}")
