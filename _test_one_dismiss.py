# -*- coding: utf-8 -*-
"""Test ONE dismiss call through the server's own API (production path)."""
import json, urllib.request

BASE = "http://127.0.0.1:5001"
snap = json.load(open('backups/dismiss_target_snapshot_v2.json', encoding='utf-8'))
chat_id = snap['targets'][0]['chat_id']
print("Test chat_id:", chat_id)

payload = json.dumps({
    "chat_id": chat_id,
    "agent_name": "Mohamed Sami",
    "reason": "Duplicate message",
}).encode('utf-8')

req = urllib.request.Request(f"{BASE}/api/chats/dismiss", data=payload,
                             headers={"Content-Type": "application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode('utf-8')
        print("HTTP", resp.status, "|", body)
except urllib.error.HTTPError as e:
    print("HTTPError", e.code, e.read().decode('utf-8'))
except Exception as e:
    print("ERROR:", type(e).__name__, e)
