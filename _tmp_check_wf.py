# -*- coding: utf-8 -*-
import automation_db
import json
import os

wfs = automation_db.list_workflows()
print("total workflows", len(wfs))
found = False
for w in wfs:
    wid = str(w.get("id") or "")
    name = str(w.get("name") or "")
    blob = (wid + " " + name).lower()
    if any(x in blob for x in ("new_ads", "religious_new", "followup", "follow_up")):
        found = True
        print("---")
        print("id:", wid)
        print("name:", name.encode("ascii", "replace").decode("ascii"))
        print("enabled:", w.get("enabled"))
        print("trigger:", w.get("trigger_type"))
        print("trigger_config:", w.get("trigger_config_json") or w.get("trigger_config"))
        print("updated_at:", w.get("updated_at"))
        steps = w.get("steps_json") or "[]"
        print("steps:", steps[:300])

if not found:
    print("NOT FOUND religious_new_ads_followup_v1")
    # show any religious workflows
    for w in wfs:
        wid = str(w.get("id") or "")
        if "religious" in wid.lower() or "follow" in wid.lower():
            print("candidate:", wid, "enabled=", w.get("enabled"))

# state file
path = "religious_new_ads_followup_state.json"
if os.path.exists(path):
    d = json.load(open(path, "r", encoding="utf-8"))
    chats = d.get("chats") if isinstance(d, dict) else None
    print("STATE chats:", len(chats) if isinstance(chats, dict) else chats)
    meta = {k: d.get(k) for k in d if k != "chats"} if isinstance(d, dict) else {}
    print("STATE meta:", json.dumps(meta, ensure_ascii=True, default=str)[:800])
else:
    print("STATE FILE MISSING")

# config
cfg = "religious_new_ads_followup_config.json"
if os.path.exists(cfg):
    print("CONFIG:", open(cfg, encoding="utf-8").read()[:500])
