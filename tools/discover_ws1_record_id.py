# -*- coding: utf-8 -*-
"""Quick discover Baserow workspace tables + Record ID fields."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import BaserowApi, load_config  # noqa: E402


def main() -> int:
    cfg = load_config()
    br = BaserowApi.from_config(cfg["baserow"])
    db_id = int((cfg.get("baserow") or {}).get("database_id") or 5)
    out = {"database_id": db_id, "tables": []}
    for t in br.list_tables(db_id):
        tid = int(t["id"])
        name = str(t.get("name") or "")
        if "import report" in name.lower():
            continue
        fields = br.list_fields(tid)
        fnames = [str(f.get("name") or "") for f in fields]
        out["tables"].append(
            {
                "id": tid,
                "name": name,
                "has_Record_ID": "Record ID" in fnames,
                "has_airtable_record_id": "airtable_record_id" in fnames,
                "field_count": len(fnames),
            }
        )
    path = ROOT / "tools" / "_baserow_ws1_tables.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
