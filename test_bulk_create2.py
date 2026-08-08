import requests
import json

url = "http://127.0.0.1:5001/api/payments/bulk_create"
payload = {
    "view": "Ägypten & FTS Invoice",
    "max_records": 10,
    "only_if_missing_invoice": True,
    "dry_run": False,
    "amount_field": "Net Rate Price (Number Only)",
    "currency_field": "Currency"
}
try:
    r = requests.post(url, json=payload, timeout=60)
    print(r.status_code)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(e)
