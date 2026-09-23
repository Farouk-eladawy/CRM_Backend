"""Quick Tiqets API connectivity check (local + public)."""
import os
import sys

import requests

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import tiqets_api as t  # noqa: E402

cfg = t.load_tiqets_config()
key = t.resolve_tiqets_api_key(cfg)
headers = {"API-Key": key}

print("=== Tiqets config ===")
print("enabled:", cfg.get("enabled"))
print("api_key_configured:", bool(str(cfg.get("api_key") or "").strip()))
print("audio_guide_base_url:", cfg.get("audio_guide_base_url"))
print()

checks = [
    ("health_local_5005", "GET", "http://127.0.0.1:5005/health", None),
    ("products_local_5005", "GET", "http://127.0.0.1:5005/v2/products", headers),
    ("products_public", "GET", "https://api.ftstravels.com/v2/products", headers),
]

for name, method, url, hdrs in checks:
    try:
        resp = requests.request(method, url, headers=hdrs, timeout=25)
        body = resp.text
        if len(body) > 400:
            body = body[:400] + "..."
        print(f"[{name}] HTTP {resp.status_code}")
        print(body)
    except Exception as exc:
        print(f"[{name}] ERROR: {exc}")
    print()
