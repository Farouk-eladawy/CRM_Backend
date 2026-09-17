# -*- coding: utf-8 -*-
import json, os, sqlite3
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
# find automation db
cands = []
for name in ("automation.db", "automation_data.db"):
    p = os.path.join(ROOT, name)
    if os.path.exists(p):
        cands.append(p)
# also search
for dirpath, _, files in os.walk(ROOT):
    if "node_modules" in dirpath or ".git" in dirpath:
        continue
    for f in files:
        if f.endswith(".db") and "automation" in f.lower():
            cands.append(os.path.join(dirpath, f))
cands = sorted(set(cands))
print("DB candidates:", cands)

# import module path
import sys
sys.path.insert(0, ROOT)
try:
    import automation_db
    print("automation_db.DB_FILE=", getattr(automation_db, "DB_FILE", None))
    db = automation_db.DB_FILE
except Exception as e:
    print("import fail", e)
    db = cands[0] if cands else None

WID = "booking_pickup_hc_v1"
out = {"workflow": None, "counts": {}, "recent": [], "errors": []}

if db and os.path.exists(db):
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # workflow
    try:
        wf = automation_db.get_workflow(WID) if "automation_db" in sys.modules else None
    except Exception:
        wf = None
    if not wf:
        row = c.execute("SELECT * FROM automation_workflows WHERE id=?", (WID,)).fetchone()
        wf = dict(row) if row else None
    if wf:
        steps = wf.get("steps") or wf.get("steps_json")
        if isinstance(steps, str):
            try:
                steps = json.loads(steps)
            except Exception:
                pass
        out["workflow"] = {
            "id": wf.get("id"),
            "name": wf.get("name"),
            "enabled": wf.get("enabled"),
            "trigger_type": wf.get("trigger_type"),
            "trigger_config": wf.get("trigger_config") or wf.get("trigger_config_json"),
            "last_run_at": wf.get("last_run_at"),
            "last_error": wf.get("last_error"),
            "steps_types": [ (s.get("type") if isinstance(s, dict) else str(s)) for s in (steps or []) ],
            "body_views": None,
        }
        try:
            body = (steps or [{}])[0].get("body") if steps else None
            if isinstance(body, str):
                body = json.loads(body)
            if isinstance(body, dict):
                out["workflow"]["body_views"] = body.get("views")
                out["workflow"]["templates"] = body.get("templates")
                out["workflow"]["send_whatsapp"] = body.get("send_whatsapp")
                out["workflow"]["send_email"] = body.get("send_email")
        except Exception as e:
            out["workflow"]["body_parse_err"] = str(e)

    # runs
    rows = c.execute(
        """SELECT id, status, event_type, started_at, finished_at, error, event_payload_json
           FROM automation_runs WHERE workflow_id=? ORDER BY started_at DESC LIMIT 50""",
        (WID,),
    ).fetchall()
    since = "2026-09-15"
    status_counts = {}
    for r in rows:
        d = dict(r)
        st = d.get("status") or "?"
        if (d.get("started_at") or "") >= since:
            status_counts[st] = status_counts.get(st, 0) + 1
        payload = None
        try:
            payload = json.loads(d["event_payload_json"]) if d.get("event_payload_json") else None
        except Exception:
            payload = d.get("event_payload_json")
        item = {
            "id": d["id"],
            "status": st,
            "started_at": d.get("started_at"),
            "finished_at": d.get("finished_at"),
            "error": (d.get("error") or "")[:500],
        }
        # extract useful bits from payload
        if isinstance(payload, dict):
            # common shapes
            for k in ("result", "response", "http", "body", "data", "results"):
                if k in payload:
                    item[f"payload_{k}_type"] = type(payload[k]).__name__
            # string dump snippets for failed
            if st not in ("success", "ok", "completed") or d.get("error"):
                item["payload_preview"] = json.dumps(payload, ensure_ascii=False)[:1200]
        out["recent"].append(item)
        if d.get("error") or st in ("error", "failed", "failure"):
            out["errors"].append(item)
    out["counts"] = status_counts
    out["db"] = db
    conn.close()

print(json.dumps(out, ensure_ascii=False, indent=2))
with open(os.path.join(ROOT, "_diag_pickup_hc_runs.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
