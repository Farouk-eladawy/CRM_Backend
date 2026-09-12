# -*- coding: utf-8 -*-
import automation_db
import json

wfs = automation_db.list_workflows()
print("total workflows", len(wfs))
for w in wfs:
    name = (w.get("name") or "")
    wid = w.get("id") or ""
    blob = f"{wid} {name}".lower()
    if any(x in blob for x in ("new_ads", "اعلانات", "إعلانات", "متابعة", "religious")):
        print("---")
        print("id:", wid)
        print("enabled:", w.get("enabled"))
        print("name:", name)
        print("trigger:", w.get("trigger_type"))
        print("trigger_config:", w.get("trigger_config_json") or w.get("trigger_config"))
        steps = w.get("steps_json") or ""
        print("steps:", steps[:400])
