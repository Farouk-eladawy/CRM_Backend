# -*- coding: utf-8 -*-
"""Discover Baserow + Airtable tables for sync config."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.migrate_airtable_to_baserow import BaserowApi, load_config  # noqa: E402


def airtable_tables(api_key: str, base_id: str) -> list[str]:
    r = requests.get(
        f"https://api.airtable.com/v0/meta/bases/{base_id}/tables",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=120,
    )
    r.raise_for_status()
    return [str(t.get("name") or "") for t in (r.json().get("tables") or []) if t.get("name")]


def workspace_id_of(app: dict):
    w = app.get("workspace_id")
    if w:
        return w
    ws = app.get("workspace")
    if isinstance(ws, dict):
        return ws.get("id")
    return ws


def main() -> int:
    cfg = load_config()
    br_cfg = cfg["baserow"]
    at = cfg["airtable"]
    br = BaserowApi.from_config(br_cfg)

    apps = br.list_applications()
    out = {"applications": [], "databases": {}}

    for a in apps:
        app_info = {
            "id": a.get("id"),
            "type": a.get("type"),
            "name": a.get("name"),
            "workspace_id": workspace_id_of(a),
        }
        out["applications"].append(app_info)
        if str(a.get("type") or "") != "database":
            continue
        db_id = int(a["id"])
        try:
            tables = br.list_tables(db_id)
            out["databases"][str(db_id)] = {
                "name": a.get("name"),
                "workspace_id": workspace_id_of(a),
                "tables": [{"id": t.get("id"), "name": t.get("name")} for t in tables],
            }
        except Exception as exc:
            out["databases"][str(db_id)] = {
                "name": a.get("name"),
                "workspace_id": workspace_id_of(a),
                "error": str(exc),
            }

    api_key = str(at.get("api_key") or "")
    main_base = str(at.get("base_id") or "")
    rel_base = str(at.get("religious_base_id") or "")
    out["airtable_main"] = airtable_tables(api_key, main_base) if main_base else []
    out["airtable_religious"] = airtable_tables(api_key, rel_base) if rel_base else []

    # Match by exact table name
    matches = {"main": [], "religious": []}
    for db_id, info in out["databases"].items():
        if info.get("error"):
            continue
        br_names = {t["name"] for t in info.get("tables") or [] if t.get("name")}
        # skip Airtable import report tables
        br_names = {n for n in br_names if "import report" not in n.lower()}
        ws = info.get("workspace_id")
        if ws in (2, "2"):
            common = sorted(br_names & set(out["airtable_religious"]))
            matches["religious"].append({"database_id": int(db_id), "name": info.get("name"), "tables": common, "baserow_only": sorted(br_names - set(out["airtable_religious"]))})
        else:
            common = sorted(br_names & set(out["airtable_main"]))
            matches["main"].append({"database_id": int(db_id), "name": info.get("name"), "tables": common, "baserow_only": sorted(br_names - set(out["airtable_main"]))})

    out["matches"] = matches
    path = ROOT / "tools" / "_baserow_discover_out.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(matches, ensure_ascii=False, indent=2))
    print(f"\nFull dump: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
