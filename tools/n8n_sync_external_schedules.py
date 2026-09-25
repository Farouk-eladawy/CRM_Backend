#!/usr/bin/env python3
"""Write one n8n-import JSON file per enabled FTS External scheduled workflow."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from automation_engine import is_religious_workflow  # noqa: E402
from fts_paths import get_data_path  # noqa: E402

DB_FILE = get_data_path("chat_history.db")
OUT_EXTERNAL = os.path.join(ROOT, "n8n_exports", "fts_external")
OUT_INTERNAL = os.path.join(ROOT, "n8n_exports", "fts_internal")
PUBLIC_API = "https://api.ftstravels.com"


def _is_internal(wf: dict) -> bool:
    return str(wf.get("category") or "").strip().lower() == "internal"


def _rewrite_url(url: str) -> str:
    u = str(url or "").strip()
    for old in ("http://127.0.0.1:5001", "http://localhost:5001", "https://127.0.0.1:5001"):
        if u.startswith(old):
            return PUBLIC_API + u[len(old) :]
    return u


def _interval(trigger_raw: str):
    try:
        cfg = json.loads(trigger_raw or "{}")
    except Exception:
        cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    if cfg.get("every_seconds") is not None:
        secs = max(1, int(float(cfg["every_seconds"])))
        if secs % 60 == 0 and secs >= 60:
            mins = secs // 60
        else:
            return {"field": "seconds", "secondsInterval": min(secs, 3600)}
    elif cfg.get("every_minutes") is not None:
        mins = max(1, int(float(cfg["every_minutes"])))
    elif cfg.get("every_hours") is not None:
        hours = max(1, int(float(cfg["every_hours"])))
        return {"field": "hours", "hoursInterval": hours}
    else:
        mins = 15
    if mins % 60 == 0:
        return {"field": "hours", "hoursInterval": max(1, mins // 60)}
    return {"field": "minutes", "minutesInterval": min(mins, 59) if mins > 59 else mins}


def _http_nodes(wf: dict, start_x: int = 260):
    try:
        steps = json.loads(wf.get("steps_json") or "[]")
    except Exception:
        steps = []
    if not isinstance(steps, list):
        steps = []
    nodes = []
    names = []
    x = start_x
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        if str(step.get("type") or "").strip().lower() != "http_request":
            continue
        method = str(step.get("method") or "POST").upper() or "POST"
        url = _rewrite_url(step.get("url") or "")
        if not url:
            continue
        timeout_s = step.get("timeout_seconds")
        try:
            timeout_ms = int(float(timeout_s) * 1000) if timeout_s is not None else 120000
        except Exception:
            timeout_ms = 120000
        timeout_ms = max(15000, min(timeout_ms, 300000))
        headers = step.get("headers") if isinstance(step.get("headers"), dict) else {}
        header_params = []
        has_ct = False
        for k, v in headers.items():
            name = str(k or "").strip()
            if not name:
                continue
            if name.lower() == "content-type":
                has_ct = True
            header_params.append({"name": name, "value": str(v)})
        if not has_ct:
            header_params.append({"name": "Content-Type", "value": "application/json"})
        body = step.get("body")
        node_name = "HTTP" if len(names) == 0 else f"HTTP {i + 1}"
        node = {
            "parameters": {
                "method": method,
                "url": url,
                "sendHeaders": True,
                "headerParameters": {"parameters": header_params},
                "options": {"timeout": timeout_ms},
            },
            "id": str(uuid.uuid4()),
            "name": node_name,
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [x, 0],
        }
        if body is not None:
            node["parameters"]["sendBody"] = True
            node["parameters"]["specifyBody"] = "json"
            node["parameters"]["jsonBody"] = (
                json.dumps(body, ensure_ascii=False, indent=2)
                if isinstance(body, (dict, list))
                else str(body)
            )
        nodes.append(node)
        names.append(node_name)
        x += 260
    return nodes, names


def _n8n_workflow(wf: dict) -> dict:
    sched_id = str(uuid.uuid4())
    interval = _interval(wf.get("trigger_config_json") or "")
    http_nodes, http_names = _http_nodes(wf)
    if not http_nodes:
        raise ValueError("no http_request step")
    nodes = [
        {
            "parameters": {"rule": {"interval": [interval]}},
            "id": sched_id,
            "name": "Schedule Trigger",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [0, 0],
        },
        *http_nodes,
    ]
    connections = {}
    prev = "Schedule Trigger"
    for name in http_names:
        connections[prev] = {"main": [[{"node": name, "type": "main", "index": 0}]]}
        prev = name
    prefix = "FTS Internal" if _is_internal(wf) else "FTS External"
    return {
        "name": f"{prefix} | {wf['name']}",
        "nodes": nodes,
        "connections": connections,
        "pinData": {},
        "settings": {
            "executionOrder": "v1",
            "timezone": "Africa/Cairo",
        },
        "staticData": None,
        "meta": {
            "fts_workflow_id": wf["id"],
        },
        "tags": [],
    }


def load_external_schedules():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, name, description, enabled, category, company_id, trigger_type,
               trigger_config_json, steps_json
        FROM automation_workflows
        """
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        wf = dict(r)
        if str(wf.get("trigger_type") or "").strip().lower() != "schedule":
            continue
        if str(wf.get("company_id") or "fts").strip().lower() not in ("fts", ""):
            continue
        if int(wf.get("enabled") or 0) != 1:
            continue
        if is_religious_workflow(wf):
            continue
        out.append(wf)
    return out


def _reset_dir(path: str):
    os.makedirs(path, exist_ok=True)
    for old in os.listdir(path):
        if old.endswith(".json") or old == "_index.txt":
            os.remove(os.path.join(path, old))


def _write_group(rows, out_dir):
    written = []
    errors = []
    for wf in rows:
        try:
            payload = _n8n_workflow(wf)
        except Exception as e:
            errors.append(f"{wf.get('id')}: {e}")
            continue
        fname = f"{wf['id']}.json"
        path = os.path.join(out_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        written.append(fname)
    with open(os.path.join(out_dir, "_index.txt"), "w", encoding="utf-8") as f:
        for name in written:
            f.write(name + "\n")
    return written, errors


def main():
    _reset_dir(OUT_EXTERNAL)
    _reset_dir(OUT_INTERNAL)
    rows = load_external_schedules()
    internal = [w for w in rows if _is_internal(w)]
    external = [w for w in rows if not _is_internal(w)]
    written_int, errors_int = _write_group(internal, OUT_INTERNAL)
    written_ext, errors_ext = _write_group(external, OUT_EXTERNAL)
    errors = errors_int + errors_ext
    print("internal", len(written_int), OUT_INTERNAL)
    print("external", len(written_ext), OUT_EXTERNAL)
    if errors:
        print("errors", len(errors))
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
