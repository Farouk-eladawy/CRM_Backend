# -*- coding: utf-8 -*-
"""Sample Airtable Date Trip / Create Date raw values for timezone alignment."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import AirtableSource, load_config

cfg = load_config()
at = AirtableSource(cfg)
meta = at.table_by_name("List")
fields = {f["name"]: f.get("type") for f in meta.get("fields") or []}
want = [n for n in fields if "date trip" in n.lower() or n.strip().startswith("Create Date") or "real date" in n.lower()]
print("Airtable field types:")
for n in sorted(want):
    print(f"  {n!r}: {fields[n]}")

table = at.api.table(at.base_id, "List")
rows = table.all(max_records=5)
out = []
for r in rows:
    f = r.get("fields") or {}
    out.append(
        {
            "id": r.get("id"),
            "Date Trip": f.get("Date Trip"),
            "Real Date Trip": f.get("Real Date Trip"),
            "Create Date  ": f.get("Create Date  "),
            "Trip Start Time": f.get("Trip Start Time"),
        }
    )
print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
Path(ROOT / "tools" / "_airtable_date_trip_sample.json").write_text(
    json.dumps({"types": {n: fields[n] for n in want}, "rows": out}, ensure_ascii=False, indent=2, default=str),
    encoding="utf-8",
)
print("wrote tools/_airtable_date_trip_sample.json")
