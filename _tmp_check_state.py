# -*- coding: utf-8 -*-
import json
import os

path = "religious_new_ads_followup_state.json"
print("exists", os.path.exists(path), "size", os.path.getsize(path) if os.path.exists(path) else 0)
with open(path, "r", encoding="utf-8") as f:
    d = json.load(f)
print("top keys", list(d.keys()) if isinstance(d, dict) else type(d))
chats = d.get("chats") if isinstance(d, dict) else None
print("chats count", len(chats) if isinstance(chats, dict) else "n/a")
if isinstance(d, dict):
    for k, v in d.items():
        if k == "chats":
            continue
        print(f"  {k}={v}")
# sample a few chats
if isinstance(chats, dict):
    n = 0
    stopped = 0
    sent1 = 0
    sent2 = 0
    for cid, st in chats.items():
        if not isinstance(st, dict):
            continue
        if st.get("stopped"):
            stopped += 1
        fu = int(st.get("followups_sent") or st.get("sent_count") or 0)
        if fu >= 1:
            sent1 += 1
        if fu >= 2:
            sent2 += 1
        if n < 3:
            print("sample", cid, st)
            n += 1
    print("stopped", stopped, "sent>=1", sent1, "sent>=2", sent2)
