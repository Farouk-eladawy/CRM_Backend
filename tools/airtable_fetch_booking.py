import json
import sys
import urllib.parse

import requests


def main():
    booking = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not booking:
        raise SystemExit("missing booking number argument")

    with open("config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    base_id = cfg["airtable"]["base_id"]
    api_key = cfg["airtable"]["api_key"]
    table = cfg["airtable"]["tables"]["main_list"]

    formula = "{Booking Nr.}='" + booking.replace("'", "\\'") + "'"
    params = {"filterByFormula": formula, "maxRecords": 1}
    url = (
        f"https://api.airtable.com/v0/{base_id}/{urllib.parse.quote(table, safe='')}"
        + "?"
        + urllib.parse.urlencode(params)
    )

    res = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    data = res.json() if res.content else {}
    rec = (data.get("records") or [None])[0]
    out = {"status_code": res.status_code, "id": (rec or {}).get("id"), "fields": (rec or {}).get("fields")}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

