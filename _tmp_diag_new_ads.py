# -*- coding: utf-8 -*-
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import automation_db

WID = "religious_new_ads_followup_v1"
print("=== WORKFLOW ===")
wf = None
for item in automation_db.list_workflows():
    if str(item.get("id") or "") == WID:
        wf = item
        break
if not wf:
    print("NOT_FOUND")
    sys.exit(1)

for k in ("id", "name", "enabled", "trigger_type", "trigger_config_json", "last_run_at", "last_error", "updated_at", "created_at"):
    print(f"{k}={wf.get(k)}")
print("steps=", (wf.get("steps_json") or "")[:400])

print("\n=== RECENT RUNS ===")
try:
    import sqlite3
    from fts_paths import get_data_path
    db = get_data_path("chat_history.db")
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    # find runs table
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("tables_with_run=", [t for t in tables if "run" in t.lower() or "automat" in t.lower()])
    for t in tables:
        if "run" in t.lower() and "automat" in t.lower():
            cols = [c[1] for c in conn.execute(f"PRAGMA table_info({t})").fetchall()]
            print("run_table", t, "cols", cols)
            q = f"SELECT * FROM {t} WHERE workflow_id=? OR cast(workflow_id as text)=? ORDER BY rowid DESC LIMIT 12"
            try:
                rows = conn.execute(q, (WID, WID)).fetchall()
            except Exception:
                # try alternate column names
                rows = []
                for col in ("workflow_id", "automation_id", "id"):
                    if col in cols:
                        try:
                            rows = conn.execute(
                                f"SELECT * FROM {t} WHERE {col}=? ORDER BY rowid DESC LIMIT 12",
                                (WID,),
                            ).fetchall()
                            break
                        except Exception:
                            pass
            for r in rows:
                d = dict(r)
                # shorten big fields
                for key in list(d.keys()):
                    val = d[key]
                    if isinstance(val, str) and len(val) > 220:
                        d[key] = val[:220] + "..."
                print(json.dumps(d, ensure_ascii=False, default=str))
            break
    conn.close()
except Exception as e:
    print("runs_error", e)

print("\n=== CONFIG ===")
cfg_path = os.path.join(ROOT, "religious_new_ads_followup_config.json")
print(open(cfg_path, encoding="utf-8").read() if os.path.exists(cfg_path) else "missing")

print("\n=== STATE SUMMARY ===")
state_path = os.path.join(ROOT, "religious_new_ads_followup_state.json")
d = json.load(open(state_path, encoding="utf-8"))
chats = d.get("chats") or {}
now = datetime.now()
stage1 = stage2 = handled = seq = stage0 = eligible = 0
for cid, e in chats.items():
    h = int(e.get("highest_stage_sent") or 0)
    if h >= 1:
        stage1 += 1
    if h >= 2:
        stage2 += 1
    if e.get("handled"):
        handled += 1
    if e.get("sequence_done"):
        seq += 1
    if h == 0 and not e.get("handled") and not e.get("sequence_done"):
        stage0 += 1
        try:
            ts = e.get("last_customer_reply")
            if ts:
                if ts.endswith("Z"):
                    ts = ts[:-1]
                dt = datetime.fromisoformat(ts)
                hours = (now - dt).total_seconds() / 3600.0
                if 3 <= hours < 24:
                    eligible += 1
        except Exception:
            pass
print("total_chats", len(chats))
print("stage_ge1", stage1)
print("stage_ge2", stage2)
print("handled", handled)
print("sequence_done", seq)
print("stage0_unhandled", stage0)
print("approx_eligible_stage1_window", eligible)

print("\n=== DRY RUN ===")
sys.path.insert(0, os.path.join(ROOT, "workflows"))
import importlib.util
spec = importlib.util.spec_from_file_location(
    "religious_new_ads_followup",
    os.path.join(ROOT, "workflows", "religious_new_ads_followup.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
res = mod.run(None, {"dry_run": True, "limit": 40})
print(json.dumps(res, ensure_ascii=False, default=str)[:1500])
