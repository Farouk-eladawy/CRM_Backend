"""Apply Tiqets portal-derived fields to Airtable Products_Catalog (reads C:\\Temp\\airtable_tiqets_updates.json)."""
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tiqets_api as t  # noqa: E402

UPDATES = Path(r"C:\Temp\airtable_tiqets_updates.json")
RESULT = Path(r"C:\Temp\apply_result.json")


def main() -> None:
    key, base = t._load_airtable_credentials()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    table = "Products_Catalog"

    recs = []
    offset = None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        r = requests.get(
            f"https://api.airtable.com/v0/{base}/{table}",
            headers=headers,
            params=params,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        recs.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break

    by_pid = {
        str(row.get("fields", {}).get("Product ID", "")).strip(): row["id"]
        for row in recs
        if row.get("fields", {}).get("Product ID")
    }

    updates = json.loads(UPDATES.read_text(encoding="utf-8"))
    ok = 0
    failures = []

    for item in updates:
        pid = str(item["product_id"])
        rid = by_pid.get(pid)
        if not rid:
            failures.append(f"missing record {pid}")
            continue
        raw_fields = item["fields"]
        fields = {}
        for name, val in raw_fields.items():
            if val is None:
                continue
            if name in ("Tickets Table Name", "Ticket View Name"):
                continue
            if name == "Required Order Data":
                if isinstance(val, str) and val:
                    fields[name] = [val]
                elif isinstance(val, list):
                    fields[name] = val
                continue
            if name == "Description" and not str(val).strip():
                continue
            fields[name] = val

        fields["Tickets Table Name"] = ""
        fields["Ticket View Name"] = ""
        if "Required Order Data" not in fields:
            fields["Required Order Data"] = []
        if "Description" not in fields:
            fields["Description"] = ""

        try:
            pr = requests.patch(
                f"https://api.airtable.com/v0/{base}/{table}/{rid}",
                headers=headers,
                json={"fields": fields},
                timeout=60,
            )
            pr.raise_for_status()
            ok += 1
            time.sleep(0.22)
        except Exception as exc:
            failures.append(f"{pid} {exc}")

    RESULT.write_text(
        json.dumps({"updated": ok, "failures": failures}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"updated": ok, "failures": len(failures)}))


if __name__ == "__main__":
    main()
