import json
import os
import sys

import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
import tiqets_api as t  # noqa: E402

key = t.resolve_tiqets_api_key(t.load_tiqets_config())
for base in ("http://127.0.0.1:5005", "https://api.ftstravels.com"):
    try:
        r = requests.get(f"{base}/v2/products", headers={"API-Key": key}, timeout=30)
        print("===", base, "HTTP", r.status_code, "===")
        if r.status_code == 200:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        else:
            print(r.text[:500])
    except Exception as exc:
        print("===", base, "ERROR", exc)
    print()
