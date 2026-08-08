import json
import os
from datetime import datetime, timezone

import requests


def _project_root():
    return os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        )
    )


def _safe_actor_slug(actor_name):
    raw = str(actor_name or "").strip() or "u_internal"
    sanitized = []
    for ch in raw:
        if ch.isalnum() or ch in ("_", "-", "."):
            sanitized.append(ch)
        else:
            sanitized.append("_")
    return "".join(sanitized) or "u_internal"


def _schema_context_file(actor_name):
    root = _project_root()
    user_dir = os.path.join(root, "runtime", "pi_brain", "users", _safe_actor_slug(actor_name))
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, "airtable_schema_context.json")


def _read_json(file_path, fallback=None):
    fallback = {} if fallback is None else fallback
    if not file_path or not os.path.exists(file_path):
        return fallback
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload if isinstance(payload, dict) else fallback
    except Exception:
        return fallback


def _write_json(file_path, payload):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _load_config():
    config_path = os.path.join(_project_root(), "config.json")
    with open(config_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _base_targets(config, base_labels=None):
    airtable_cfg = (config.get("airtable", {}) or {})
    requested = {str(item or "").strip().lower() for item in (base_labels or []) if str(item or "").strip()}
    targets = []
    seen = set()
    for base_label, base_id in (
        ("main", airtable_cfg.get("base_id")),
        ("trips", airtable_cfg.get("trips_base_id")),
        ("religious", airtable_cfg.get("religious_base_id")),
    ):
        base_id = str(base_id or "").strip()
        if not base_id or base_id in seen:
            continue
        seen.add(base_id)
        normalized_label = str(base_label or "").strip().lower()
        if requested and normalized_label not in requested:
            continue
        targets.append({"base_label": normalized_label, "base_id": base_id})
    return targets


def _truncate_result(schema_context, max_fields_per_table):
    field_limit = max(int(max_fields_per_table or 0), 1)
    data = {
        "updated_at": schema_context.get("updated_at"),
        "summary": dict(schema_context.get("summary") or {}),
        "bases": [],
    }
    for base in (schema_context.get("bases") or []):
        base_entry = {
            "base_label": base.get("base_label"),
            "base_id": base.get("base_id"),
            "status": base.get("status"),
            "message": base.get("message"),
            "tables": [],
        }
        for table in (base.get("tables") or []):
            fields = list(table.get("fields") or [])
            table_entry = dict(table)
            table_entry["fields"] = fields[:field_limit]
            table_entry["truncated_field_count"] = max(0, len(fields) - field_limit)
            base_entry["tables"].append(table_entry)
        data["bases"].append(base_entry)
    return data


def handle_discover_airtable_schema_context(payload, actor_name):
    payload = payload if isinstance(payload, dict) else {}
    refresh = bool(payload.get("refresh"))
    include_field_options = bool(payload.get("include_field_options", True))
    target_table = str(payload.get("target_table") or "").strip()
    max_fields_per_table = int(payload.get("max_fields_per_table") or 12)
    cache_file = _schema_context_file(actor_name)
    if not refresh:
        cached = _read_json(cache_file, {})
        if cached:
            return {
                "status": "success",
                "message": "Airtable schema context loaded from cache.",
                "data": {
                    "cache_file": cache_file,
                    "cached": True,
                    "schema_context": _truncate_result(cached, max_fields_per_table),
                },
            }

    config = _load_config()
    airtable_cfg = (config.get("airtable", {}) or {})
    api_key = str(airtable_cfg.get("api_key") or "").strip()
    if not api_key:
        return {"status": "error", "message": "Missing Airtable API key in config.json."}

    blocked_update_types = {
        "formula", "rollup", "count", "createdTime", "lastModifiedTime", "multipleLookupValues",
        "lookup", "button", "autoNumber", "multipleRecordLinks", "createdBy", "lastModifiedBy"
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    schema_context = {
        "status": "success",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "bases": [],
        "summary": {"base_count": 0, "table_count": 0, "field_count": 0},
    }

    for target in _base_targets(config, base_labels=payload.get("base_labels")):
        base_label = str(target.get("base_label") or "").strip()
        base_id = str(target.get("base_id") or "").strip()
        meta_url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        try:
            resp = requests.get(meta_url, headers=headers, timeout=30)
            if resp.status_code != 200:
                schema_context["bases"].append({
                    "base_label": base_label,
                    "base_id": base_id,
                    "status": "error",
                    "message": resp.text[:500],
                    "tables": [],
                })
                continue
            payload_json = resp.json() or {}
            base_entry = {
                "base_label": base_label,
                "base_id": base_id,
                "status": "success",
                "tables": [],
            }
            for table in (payload_json.get("tables") or []):
                table_name = str(table.get("name") or "").strip()
                if target_table and table_name.lower() != target_table.lower():
                    continue
                table_entry = {
                    "table_id": str(table.get("id") or "").strip(),
                    "table_name": table_name,
                    "primary_field_id": str(table.get("primaryFieldId") or "").strip(),
                    "field_count": 0,
                    "fields": [],
                    "suggested_update_fields": [],
                }
                for field in (table.get("fields") or []):
                    field_type = str(field.get("type") or "").strip()
                    options = field.get("options") if isinstance(field.get("options"), dict) else {}
                    field_entry = {
                        "field_id": str(field.get("id") or "").strip(),
                        "field_name": str(field.get("name") or ""),
                        "field_type": field_type,
                        "is_updatable": field_type not in blocked_update_types,
                    }
                    if include_field_options:
                        choices = [str(choice.get("name") or "").strip() for choice in (options.get("choices") or []) if str(choice.get("name") or "").strip()]
                        if choices:
                            field_entry["choices"] = choices[:50]
                    linked_table_id = str(options.get("linkedTableId") or "").strip()
                    if linked_table_id:
                        field_entry["linked_table_id"] = linked_table_id
                    table_entry["fields"].append(field_entry)
                    if field_entry["is_updatable"]:
                        table_entry["suggested_update_fields"].append({
                            "field_id": field_entry["field_id"],
                            "field_name": field_entry["field_name"],
                            "field_type": field_entry["field_type"],
                            "choices": list(field_entry.get("choices") or [])[:10],
                        })
                table_entry["field_count"] = len(table_entry["fields"])
                base_entry["tables"].append(table_entry)
            schema_context["bases"].append(base_entry)
        except Exception as exc:
            schema_context["bases"].append({
                "base_label": base_label,
                "base_id": base_id,
                "status": "error",
                "message": str(exc)[:500],
                "tables": [],
            })

    schema_context["summary"]["base_count"] = len(schema_context["bases"])
    schema_context["summary"]["table_count"] = sum(len(base.get("tables") or []) for base in schema_context["bases"])
    schema_context["summary"]["field_count"] = sum(len(table.get("fields") or []) for base in schema_context["bases"] for table in (base.get("tables") or []))
    _write_json(cache_file, schema_context)
    return {
        "status": "success",
        "message": "Airtable schema context discovered and cached successfully.",
        "data": {
            "cache_file": cache_file,
            "cached": False,
            "schema_context": _truncate_result(schema_context, max_fields_per_table),
        },
    }
