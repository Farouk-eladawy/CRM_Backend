# -*- coding: utf-8 -*-
"""Check ahmed1/ahmed2 template status on Meta (Religious WABA)."""
import json
import sys
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cfg = json.load(open("config.json", encoding="utf-8"))
tok = cfg["whatsapp"]["access_token"]

for name in ["ahmed2", "ahmed1"]:
    url = f"https://graph.facebook.com/v21.0/4487473721533334/message_templates?name={name}&access_token={tok}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace"))
        tmpls = data.get("data") or []
        print(f"=== {name}: {len(tmpls)} template(s) ===")
        for t in tmpls:
            info = {
                "id": t.get("id"),
                "name": t.get("name"),
                "status": t.get("status"),
                "language": t.get("language"),
                "category": t.get("category"),
                "components": t.get("components"),
            }
            print(json.dumps(info, ensure_ascii=False, indent=1)[:3000])
    except urllib.error.HTTPError as e:
        print(name, "HTTP", e.code, e.read().decode("utf-8", errors="replace")[:300])
