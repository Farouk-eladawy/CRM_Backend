import ast
import csv
import json
import os
from datetime import datetime, timezone
from urllib.parse import quote

import requests


READ_ONLY_TYPES = {
    "formula",
    "rollup",
    "lookup",
    "count",
    "autoNumber",
    "createdTime",
    "lastModifiedTime",
    "createdBy",
    "lastModifiedBy",
    "button",
    "multipleLookupValues",
}


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


def _actor_dir(actor_name):
    path = os.path.join(_project_root(), "runtime", "pi_brain", "users", _safe_actor_slug(actor_name))
    os.makedirs(path, exist_ok=True)
    return path


def _schema_context_file(actor_name):
    return os.path.join(_actor_dir(actor_name), "airtable_schema_context.json")


def _audit_output_file(actor_name, booking_number):
    safe_booking = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(booking_number or "").strip()) or "unknown"
    return os.path.join(_actor_dir(actor_name), f"main_list_audit_{safe_booking}.json")


def _load_config():
    path = os.path.join(_project_root(), "config.json")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


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


def _load_csv_fields():
    csv_path = os.path.join(_project_root(), "Airtable Fields.csv")
    if not os.path.exists(csv_path):
        return []
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            field_name = str((row or {}).get("name") or "").strip()
            field_id = str((row or {}).get("id") or "").strip()
            field_type = str((row or {}).get("type") or "").strip()
            if not field_name:
                continue
            rows.append({
                "field_id": field_id,
                "field_name": field_name,
                "field_type": field_type,
            })
    return rows


def _load_python_field_mapping():
    try:
        from airtable_fields import ID_TO_READABLE_NAME
    except Exception:
        return {}
    out = {}
    for field_id, field_name in (ID_TO_READABLE_NAME or {}).items():
        field_id_str = str(field_id or "").strip()
        field_name_str = str(field_name or "").strip()
        if field_id_str and field_name_str:
            out[field_id_str] = field_name_str
    return out


def _ensure_main_schema_context(actor_name, refresh=False):
    cache_file = _schema_context_file(actor_name)
    cached = _read_json(cache_file, {})
    if isinstance(cached, dict) and cached.get("bases") and not refresh:
        sanitized_cached = _sanitize_schema_context(cached)
        for base in (sanitized_cached.get("bases") or []):
            if str(base.get("base_label") or "").strip().lower() != "main":
                continue
            for table in (base.get("tables") or []):
                if str(table.get("table_name") or "").strip() == "List":
                    return sanitized_cached
        refresh = True
    from runtime.pi_brain.dynamic_handlers.discover_airtable_schema_context import handle_discover_airtable_schema_context

    result = handle_discover_airtable_schema_context(
        {
            "refresh": bool(refresh),
            "base_labels": ["main"],
            "include_field_options": True,
            "max_fields_per_table": 500,
        },
        actor_name,
    )
    data = (result or {}).get("data") if isinstance(result, dict) else {}
    schema_context = _read_json(cache_file, {})
    if isinstance(schema_context, dict) and schema_context.get("bases"):
        sanitized = _sanitize_schema_context(schema_context)
        try:
            _write_json(cache_file, sanitized)
        except Exception:
            pass
        return sanitized
    return _sanitize_schema_context(data.get("schema_context") if isinstance(data, dict) else {})


def _coerce_schema_node(node):
    if isinstance(node, dict):
        return {key: _coerce_schema_node(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_coerce_schema_node(value) for value in node]
    if isinstance(node, str):
        trimmed = node.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            try:
                parsed = ast.literal_eval(trimmed)
                return _coerce_schema_node(parsed)
            except Exception:
                return node
        if trimmed.startswith("[") and trimmed.endswith("]"):
            try:
                parsed = ast.literal_eval(trimmed)
                return _coerce_schema_node(parsed)
            except Exception:
                return node
    return node


def _sanitize_schema_context(schema_context):
    schema_context = _coerce_schema_node(schema_context if isinstance(schema_context, dict) else {})
    bases = []
    for base in (schema_context.get("bases") or []):
        if not isinstance(base, dict):
            continue
        tables = []
        for table in (base.get("tables") or []):
            if not isinstance(table, dict):
                continue
            fields = [field for field in (table.get("fields") or []) if isinstance(field, dict)]
            suggested = [item for item in (table.get("suggested_update_fields") or []) if isinstance(item, dict)]
            table["fields"] = fields
            table["suggested_update_fields"] = suggested
            tables.append(table)
        base["tables"] = tables
        bases.append(base)
    schema_context["bases"] = bases
    return schema_context


def _get_main_table_meta(actor_name, refresh=False):
    schema_context = _ensure_main_schema_context(actor_name, refresh=refresh)
    for base in (schema_context.get("bases") or []):
        if str(base.get("base_label") or "").strip().lower() != "main":
            continue
        for table in (base.get("tables") or []):
            if str(table.get("table_name") or "").strip() == "List":
                return schema_context, base, table
    return schema_context, {}, {}


def _auth_headers(api_key, content_type=False):
    headers = {"Authorization": f"Bearer {api_key}"}
    if content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _main_table_url(base_id, table_name="List"):
    return f"https://api.airtable.com/v0/{base_id}/{quote(str(table_name or 'List'))}"


def _fetch_booking_by_number(config, booking_number):
    airtable_cfg = (config.get("airtable", {}) or {})
    api_key = str(airtable_cfg.get("api_key") or "").strip()
    base_id = str(airtable_cfg.get("base_id") or "").strip()
    table_name = str(((airtable_cfg.get("tables") or {}).get("main_list")) or "List").strip() or "List"
    booking_value = str(booking_number or "").strip()
    if not api_key or not base_id or not booking_value:
        return None
    safe_booking_value = booking_value.replace("'", "\\'")
    formula = f"{{Booking Nr.}}='{safe_booking_value}'"
    url = _main_table_url(base_id, table_name)
    resp = requests.get(
        url,
        headers=_auth_headers(api_key),
        params={"filterByFormula": formula, "maxRecords": 1},
        timeout=30,
    )
    resp.raise_for_status()
    records = (resp.json() or {}).get("records") or []
    if not records:
        return None
    record = records[0]
    record["table_name"] = table_name
    record["base_id"] = base_id
    return record


def _resolve_record(config, booking_number=None, record_id=None):
    if booking_number:
        record = _fetch_booking_by_number(config, booking_number)
        if record:
            return record
    if record_id:
        airtable_cfg = (config.get("airtable", {}) or {})
        api_key = str(airtable_cfg.get("api_key") or "").strip()
        base_id = str(airtable_cfg.get("base_id") or "").strip()
        table_name = str(((airtable_cfg.get("tables") or {}).get("main_list")) or "List").strip() or "List"
        url = f"{_main_table_url(base_id, table_name)}/{record_id}"
        resp = requests.get(url, headers=_auth_headers(api_key), timeout=30)
        resp.raise_for_status()
        record = resp.json() or {}
        record["table_name"] = table_name
        record["base_id"] = base_id
        return record
    return None


def _table_lookup_maps(table_meta):
    by_name = {}
    by_name_lower = {}
    by_id = {}
    for field in (table_meta.get("fields") or []):
        field_name = str(field.get("field_name") or "")
        field_id = str(field.get("field_id") or "").strip()
        if field_name:
            by_name[field_name] = field
            by_name_lower[field_name.strip().lower()] = field
        if field_id:
            by_id[field_id] = field
    return by_name, by_name_lower, by_id


def _canonical_field_name(field_name, table_meta):
    """
    Resolve a field name to its EXACT Airtable API name.
    Airtable field names may have trailing spaces (e.g. 'Reason ', 'Create Date  ').
    The PATCH API requires the exact name including trailing whitespace.
    """
    if not isinstance(field_name, str):
        return field_name
    by_name, by_name_lower, by_id = _table_lookup_maps(table_meta)
    trimmed = field_name.strip()
    # 1. Try the user-supplied name as-is (important if they already know the trailing-space form)
    if field_name in by_name:
        return field_name
    # 2. Search live fields: matching by trimmed+lowered returns the EXACT live field name
    for live_field in (table_meta.get("fields") or []):
        live_name = str(live_field.get("field_name") or "")
        if live_name.strip().lower() == trimmed.lower():
            return live_name  # Return exact Airtable name (preserves trailing spaces)
    # 3. Fallback: trimmed + by_name
    if trimmed in by_name:
        return trimmed
    lowered = trimmed.lower()
    if lowered in by_name_lower:
        return str((by_name_lower.get(lowered) or {}).get("field_name") or trimmed)
    if trimmed in by_id:
        return str((by_id.get(trimmed) or {}).get("field_name") or trimmed)
    return trimmed


def _field_meta(field_name, table_meta):
    canonical = _canonical_field_name(field_name, table_meta)
    by_name, _, _ = _table_lookup_maps(table_meta)
    return by_name.get(canonical) or {}


def _coerce_value_for_field(field_meta, value):
    field_type = str((field_meta or {}).get("field_type") or "").strip()
    if field_type == "multipleSelects":
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        normalized = str(value or "").strip()
        return [normalized] if normalized else []
    if field_type == "multipleAttachments":
        if isinstance(value, list):
            out = []
            for item in value:
                if isinstance(item, dict) and str(item.get("url") or "").strip():
                    out.append({"url": str(item.get("url") or "").strip()})
                elif isinstance(item, str) and item.strip():
                    out.append({"url": item.strip()})
            return out
    if field_type == "multipleRecordLinks":
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        normalized = str(value or "").strip()
        return [normalized] if normalized else []
    if field_type in {"number", "currency", "percent"}:
        if value in ("", None):
            return None
        try:
            if isinstance(value, (int, float)):
                return value
            txt = str(value).strip().replace(",", "")
            return float(txt) if "." in txt else int(txt)
        except Exception:
            return value
    if field_type == "checkbox":
        if isinstance(value, bool):
            return value
        txt = str(value or "").strip().lower()
        return txt in {"1", "true", "yes", "y", "on", "checked", "موافق", "نعم"}
    return value


def _normalize_update_fields(fields, table_meta):
    fields = fields if isinstance(fields, dict) else {}
    normalized = {}
    for raw_name, raw_value in fields.items():
        canonical = _canonical_field_name(raw_name, table_meta)
        meta = _field_meta(canonical, table_meta)
        normalized[canonical] = _coerce_value_for_field(meta, raw_value)
    return normalized


def _fetch_live_airtable_field_names(api_key, base_id, table_name):
    """Fetch the actual field names from Airtable meta API to get exact names (with trailing spaces)."""
    try:
        url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
        resp = requests.get(url, headers=_auth_headers(api_key), timeout=30)
        resp.raise_for_status()
        tables = (resp.json() or {}).get("tables") or []
        for tbl in tables:
            if tbl.get("name") == table_name:
                field_map = {}
                for f in (tbl.get("fields") or []):
                    fn = str(f.get("name") or "").strip()
                    actual = str(f.get("name") or "")
                    if fn:
                        field_map[fn.lower()] = actual
                return field_map
    except Exception:
        return None
    return None


def _patch_record_fields(config, record_id, fields):
    airtable_cfg = (config.get("airtable", {}) or {})
    api_key = str(airtable_cfg.get("api_key") or "").strip()
    base_id = str(airtable_cfg.get("base_id") or "").strip()
    table_name = str(((airtable_cfg.get("tables") or {}).get("main_list")) or "List").strip() or "List"
    url = f"{_main_table_url(base_id, table_name)}/{record_id}"
    resp = requests.patch(
        url,
        headers=_auth_headers(api_key, content_type=True),
        json={"fields": fields, "typecast": True},
        timeout=30,
    )
    # Handle 422 UNKNOWN_FIELD_NAME: retry with exact field names from live Airtable metadata
    if resp.status_code == 422:
        error_body = resp.json() or {}
        error_type = (((error_body.get("error") or {})).get("type") or "").strip()
        if error_type == "UNKNOWN_FIELD_NAME":
            live_names = _fetch_live_airtable_field_names(api_key, base_id, table_name)
            if live_names:
                retry_fields = {}
                for key, value in fields.items():
                    key_lower = key.strip().lower()
                    exact_name = live_names.get(key_lower)
                    if exact_name:
                        retry_fields[exact_name] = value
                    else:
                        retry_fields[key] = value
                if retry_fields and retry_fields != fields:
                    resp = requests.patch(
                        url,
                        headers=_auth_headers(api_key, content_type=True),
                        json={"fields": retry_fields, "typecast": True},
                        timeout=30,
                    )
                    if resp.status_code < 400:
                        return resp.json() or {}
    resp.raise_for_status()
    return resp.json() or {}


def _fetch_records(config, fields=None, max_records=50):
    airtable_cfg = (config.get("airtable", {}) or {})
    api_key = str(airtable_cfg.get("api_key") or "").strip()
    base_id = str(airtable_cfg.get("base_id") or "").strip()
    table_name = str(((airtable_cfg.get("tables") or {}).get("main_list")) or "List").strip() or "List"
    url = _main_table_url(base_id, table_name)
    params = {"pageSize": min(max(int(max_records or 1), 1), 100)}
    if fields:
        params["fields[]"] = list(fields)
    resp = requests.get(url, headers=_auth_headers(api_key), params=params, timeout=30)
    resp.raise_for_status()
    return (resp.json() or {}).get("records") or []


def _filter_records(records, filters, table_meta):
    filters = filters if isinstance(filters, list) else []
    if not filters:
        return records
    out = []
    for record in records:
        fields = (record or {}).get("fields") or {}
        matched = True
        for item in filters:
            if not isinstance(item, dict):
                continue
            field_name = _canonical_field_name(item.get("field_name"), table_meta)
            operator = str(item.get("operator") or "eq").strip().lower()
            target_value = item.get("value")
            current_value = fields.get(field_name)
            current_text = ", ".join(str(x).strip() for x in current_value if str(x).strip()) if isinstance(current_value, list) else str(current_value or "").strip()
            target_text = ", ".join(str(x).strip() for x in target_value if str(x).strip()) if isinstance(target_value, list) else str(target_value or "").strip()
            if operator == "eq":
                matched = current_text.lower() == target_text.lower()
            elif operator == "contains":
                matched = target_text.lower() in current_text.lower()
            elif operator == "in":
                source_values = [str(x).strip().lower() for x in (current_value if isinstance(current_value, list) else [current_value]) if str(x).strip()]
                target_values = [str(x).strip().lower() for x in (target_value if isinstance(target_value, list) else [target_value]) if str(x).strip()]
                matched = any(item_value in source_values for item_value in target_values)
            elif operator == "not_empty":
                matched = bool(current_text)
            else:
                matched = False
            if not matched:
                break
        if matched:
            out.append(record)
    return out


def _resolve_linked_table(base_meta, linked_table_id):
    linked_id = str(linked_table_id or "").strip()
    if not linked_id:
        return {}
    for table in (base_meta.get("tables") or []):
        if str(table.get("table_id") or "").strip() == linked_id:
            return table
    return {}


def _fetch_linked_records(config, linked_table, record_ids):
    airtable_cfg = (config.get("airtable", {}) or {})
    api_key = str(airtable_cfg.get("api_key") or "").strip()
    base_id = str(airtable_cfg.get("base_id") or "").strip()
    table_name = str(linked_table.get("table_name") or linked_table.get("table_id") or "").strip()
    if not api_key or not base_id or not table_name:
        return []
    headers = _auth_headers(api_key)
    out = []
    for record_id in record_ids[:20]:
        url = f"https://api.airtable.com/v0/{base_id}/{quote(table_name)}/{quote(str(record_id).strip())}"
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            out.append(resp.json() or {})
    return out


def _create_record(config, table_name, fields):
    airtable_cfg = (config.get("airtable", {}) or {})
    api_key = str(airtable_cfg.get("api_key") or "").strip()
    base_id = str(airtable_cfg.get("base_id") or "").strip()
    url = _main_table_url(base_id, table_name)
    resp = requests.post(
        url,
        headers=_auth_headers(api_key, content_type=True),
        json={"fields": fields, "typecast": True},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json() or {}


def _summarize_record(record, table_meta):
    record = record if isinstance(record, dict) else {}
    fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
    populated = []
    empty = []
    linked = []
    attachments = []
    for field in (table_meta.get("fields") or []):
        field_name = str(field.get("field_name") or "").strip()
        value = fields.get(field_name)
        if value in ("", None, [], {}):
            empty.append(field_name)
            continue
        populated.append(field_name)
        field_type = str(field.get("field_type") or "").strip()
        if field_type == "multipleRecordLinks":
            linked.append({"field_name": field_name, "count": len(value) if isinstance(value, list) else 1})
        if field_type == "multipleAttachments":
            attachments.append({"field_name": field_name, "count": len(value) if isinstance(value, list) else 1})
    return {
        "record_id": str(record.get("id") or "").strip(),
        "booking_number": str(fields.get("Booking Nr.") or "").strip(),
        "customer_name": str(fields.get("Customer Name") or "").strip(),
        "trip_name": str(fields.get("trip Name") or fields.get("Real Product Name") or "").strip(),
        "booking_status": str(fields.get("Booking Status") or "").strip(),
        "date_trip": str(fields.get("Date Trip") or "").strip(),
        "populated_field_count": len(populated),
        "empty_field_count": len(empty),
        "linked_fields": linked,
        "attachment_fields": attachments,
        "high_signal_fields": {
            key: fields.get(key)
            for key in [
                "Agency",
                "Booking Nr.",
                "Date Trip",
                "trip Name",
                "Customer Name",
                "Hotel Name",
                "Customer personal email",
                "Customer Phone",
                "Booking Status",
                "No show & refund",
                "Attachments",
                "Attachments Chat",
            ]
            if key in fields
        },
    }


def _suggest_actions(record, table_meta):
    summary = _summarize_record(record, table_meta)
    suggestions = []
    fields = ((record or {}).get("fields") or {}) if isinstance(record, dict) else {}
    if not fields.get("Customer personal email") and fields.get("Customer Email"):
        suggestions.append("اقتراح تحديث `Customer personal email` من البريد الحالي إذا كان بريدًا شخصيًا.")
    if not fields.get("Hotel Name"):
        suggestions.append("اقتراح تحديث `Hotel Name` لأن الحقل فارغ ويؤثر على التشغيل.")
    if not fields.get("No show & refund"):
        suggestions.append("يمكن تحديث `No show & refund` إذا كان الطلب متعلقًا بعدم الحضور أو الاسترداد.")
    if fields.get("Attachments") or fields.get("Attachments Chat"):
        suggestions.append("يمكن استخراج أو مراجعة المرفقات من `Attachments` و`Attachments Chat`.")
    if summary.get("linked_fields"):
        suggestions.append("يمكن تتبع السجلات المرتبطة مثل السائق/المرشد/المورد/التذاكر عبر `follow_links`.")
    suggestions.append("يمكن استخدام `list_updatable_fields` لإظهار الحقول القابلة للتعديل مع الأنواع والخيارات.")
    suggestions.append("يمكن استخدام `filter_records` لتصفية الحجوزات بحسب الوكالة أو التاريخ أو الحالة أو الدفع.")
    return suggestions[:8]


def _audit_against_sources(record, table_meta):
    csv_fields = _load_csv_fields()
    python_mapping = _load_python_field_mapping()
    live_fields = list(table_meta.get("fields") or [])
    live_by_name = {str(field.get("field_name") or "").strip(): field for field in live_fields}
    live_by_trimmed = {str(field.get("field_name") or "").strip().strip(): field for field in live_fields}
    live_by_lower = {str(field.get("field_name") or "").strip().lower(): field for field in live_fields}

    csv_report = {"matched": [], "canonical_only": [], "missing": []}
    for item in csv_fields:
        field_name = str(item.get("field_name") or "").strip()
        exact = live_by_name.get(field_name)
        trimmed = live_by_trimmed.get(field_name.strip())
        lowered = live_by_lower.get(field_name.strip().lower())
        if exact:
            csv_report["matched"].append(field_name)
        elif trimmed or lowered:
            canonical = (trimmed or lowered or {}).get("field_name")
            csv_report["canonical_only"].append({"source_name": field_name, "canonical_live_name": canonical})
        else:
            csv_report["missing"].append(field_name)

    mapping_report = {"matched": [], "canonical_only": [], "missing": [], "suspicious_ids": []}
    for field_id, mapped_name in python_mapping.items():
        exact = live_by_name.get(mapped_name)
        trimmed = live_by_trimmed.get(mapped_name.strip())
        lowered = live_by_lower.get(mapped_name.strip().lower())
        if exact:
            mapping_report["matched"].append(mapped_name)
        elif trimmed or lowered:
            canonical = (trimmed or lowered or {}).get("field_name")
            mapping_report["canonical_only"].append({"field_id": field_id, "mapped_name": mapped_name, "canonical_live_name": canonical})
        else:
            mapping_report["missing"].append({"field_id": field_id, "mapped_name": mapped_name})
        if mapped_name.startswith("fld"):
            mapping_report["suspicious_ids"].append({"field_id": field_id, "mapped_name": mapped_name})

    fields = (record.get("fields") or {}) if isinstance(record, dict) else {}
    live_field_audit = []
    for field in live_fields:
        field_name = str(field.get("field_name") or "").strip()
        field_type = str(field.get("field_type") or "").strip()
        value = fields.get(field_name)
        live_field_audit.append({
            "field_id": str(field.get("field_id") or "").strip(),
            "field_name": field_name,
            "field_type": field_type,
            "is_updatable": bool(field.get("is_updatable")),
            "has_value_in_record": value not in ("", None, [], {}),
            "value_preview": (", ".join(str(x).strip() for x in value[:3]) if isinstance(value, list) else str(value or ""))[:200],
            "linked_table_id": str(field.get("linked_table_id") or "").strip(),
            "choices": list(field.get("choices") or [])[:15],
        })

    return {
        "csv_report": csv_report,
        "python_mapping_report": mapping_report,
        "live_field_audit": live_field_audit,
    }


def handle_manage_main_bookings_schema_aware(payload, actor_name):
    payload = payload if isinstance(payload, dict) else {}
    operation = str(payload.get("operation") or "audit_record").strip()
    config = _load_config()
    schema_context, base_meta, table_meta = _get_main_table_meta(actor_name, refresh=bool(payload.get("refresh_schema")))
    if not table_meta:
        return {
            "status": "error",
            "message": "Main/List schema metadata is unavailable.",
        }

    booking_number = str(payload.get("booking_number") or "").strip()
    record_id = str(payload.get("record_id") or "").strip()
    record = None
    if operation in {"audit_record", "get_field", "get_record_summary", "suggest_actions", "update_fields", "follow_links", "create_linked_record"}:
        record = _resolve_record(config, booking_number=booking_number, record_id=record_id)
        if not record:
            return {"status": "error", "message": "Booking record was not found in Main/List."}

    if operation == "audit_record":
        audit_report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "actor_name": _safe_actor_slug(actor_name),
            "table_name": "List",
            "base_id": str((config.get("airtable", {}) or {}).get("base_id") or "").strip(),
            "record_summary": _summarize_record(record, table_meta),
            "source_audit": _audit_against_sources(record, table_meta),
        }
        audit_file = _audit_output_file(actor_name, booking_number or record.get("id"))
        _write_json(audit_file, audit_report)
        return {
            "status": "success",
            "message": "Main/List audit completed successfully.",
            "data": {
                "audit_file": audit_file,
                "record_summary": audit_report["record_summary"],
                "csv_missing_count": len(audit_report["source_audit"]["csv_report"]["missing"]),
                "mapping_missing_count": len(audit_report["source_audit"]["python_mapping_report"]["missing"]),
                "mapping_suspicious_count": len(audit_report["source_audit"]["python_mapping_report"]["suspicious_ids"]),
            },
        }

    if operation == "list_updatable_fields":
        suggested = []
        for field in (table_meta.get("fields") or []):
            if not field.get("is_updatable"):
                continue
            suggested.append({
                "field_name": str(field.get("field_name") or "").strip(),
                "field_type": str(field.get("field_type") or "").strip(),
                "choices": list(field.get("choices") or [])[:10],
                "linked_table_id": str(field.get("linked_table_id") or "").strip(),
            })
        return {
            "status": "success",
            "message": "Updatable fields for Main/List prepared successfully.",
            "data": {"fields": suggested},
        }

    if operation == "get_record_summary":
        return {
            "status": "success",
            "message": "Booking summary prepared successfully.",
            "data": {"summary": _summarize_record(record, table_meta)},
        }

    if operation == "get_field":
        requested_fields = payload.get("field_names")
        if isinstance(requested_fields, str):
            requested_fields = [requested_fields]
        requested_fields = requested_fields if isinstance(requested_fields, list) else []
        fields = (record.get("fields") or {}) if isinstance(record, dict) else {}
        out = {}
        for item in requested_fields[:25]:
            canonical = _canonical_field_name(item, table_meta)
            out[canonical] = fields.get(canonical)
        return {
            "status": "success",
            "message": "Requested field values extracted successfully.",
            "data": {"record_id": record.get("id"), "fields": out},
        }

    if operation == "suggest_actions":
        return {
            "status": "success",
            "message": "Schema-aware suggestions prepared successfully.",
            "data": {
                "summary": _summarize_record(record, table_meta),
                "suggestions": _suggest_actions(record, table_meta),
            },
        }

    if operation == "filter_records":
        field_names = []
        filters = payload.get("filters")
        for item in (filters or []):
            if isinstance(item, dict) and item.get("field_name"):
                field_names.append(_canonical_field_name(item.get("field_name"), table_meta))
        field_names.extend(["Booking Nr.", "Customer Name", "trip Name", "Booking Status", "Date Trip"])
        unique_fields = []
        seen_fields = set()
        for field_name in field_names:
            if field_name and field_name not in seen_fields:
                seen_fields.add(field_name)
                unique_fields.append(field_name)
        records = _fetch_records(config, fields=unique_fields, max_records=payload.get("max_records") or 50)
        filtered = _filter_records(records, filters, table_meta)
        compact = []
        for item in filtered[: int(payload.get("result_limit") or 20)]:
            fields = (item.get("fields") or {}) if isinstance(item, dict) else {}
            compact.append({
                "record_id": str(item.get("id") or "").strip(),
                "Booking Nr.": fields.get("Booking Nr."),
                "Customer Name": fields.get("Customer Name"),
                "trip Name": fields.get("trip Name"),
                "Booking Status": fields.get("Booking Status"),
                "Date Trip": fields.get("Date Trip"),
            })
        return {
            "status": "success",
            "message": f"Filtered {len(filtered)} record(s) from Main/List.",
            "data": {"records": compact, "matched_count": len(filtered)},
        }

    if operation == "update_fields":
        raw_fields = payload.get("fields")
        normalized_fields = _normalize_update_fields(raw_fields, table_meta)
        blocked = []
        for field_name in list(normalized_fields.keys()):
            meta = _field_meta(field_name, table_meta)
            if not meta:
                blocked.append({"field_name": field_name, "reason": "unknown_field"})
                normalized_fields.pop(field_name, None)
                continue
            if str(meta.get("field_type") or "").strip() in READ_ONLY_TYPES:
                blocked.append({"field_name": field_name, "reason": "read_only"})
                normalized_fields.pop(field_name, None)
        if not normalized_fields:
            return {
                "status": "error",
                "message": "No valid updatable fields remained after schema validation.",
                "data": {"blocked_fields": blocked},
            }
        updated_record = _patch_record_fields(config, str(record.get("id") or "").strip(), normalized_fields)
        return {
            "status": "success",
            "message": "Main/List record updated successfully.",
            "data": {
                "record_id": str(updated_record.get("id") or "").strip(),
                "applied_fields": normalized_fields,
                "blocked_fields": blocked,
            },
        }

    if operation == "follow_links":
        requested_fields = payload.get("field_names")
        if isinstance(requested_fields, str):
            requested_fields = [requested_fields]
        requested_fields = requested_fields if isinstance(requested_fields, list) else []
        fields = (record.get("fields") or {}) if isinstance(record, dict) else {}
        link_data = []
        for item in requested_fields[:10]:
            canonical = _canonical_field_name(item, table_meta)
            meta = _field_meta(canonical, table_meta)
            if str(meta.get("field_type") or "").strip() != "multipleRecordLinks":
                continue
            linked_table = _resolve_linked_table(base_meta, meta.get("linked_table_id"))
            record_ids = fields.get(canonical) if isinstance(fields.get(canonical), list) else []
            linked_records = _fetch_linked_records(config, linked_table, record_ids)
            compact_records = []
            for linked_record in linked_records:
                linked_fields = (linked_record.get("fields") or {}) if isinstance(linked_record, dict) else {}
                compact_records.append({
                    "record_id": str(linked_record.get("id") or "").strip(),
                    "fields_preview": {key: linked_fields.get(key) for key in list(linked_fields.keys())[:8]},
                })
            link_data.append({
                "field_name": canonical,
                "linked_table_id": str(meta.get("linked_table_id") or "").strip(),
                "linked_table_name": str(linked_table.get("table_name") or "").strip(),
                "record_count": len(compact_records),
                "records": compact_records,
            })
        return {
            "status": "success",
            "message": "Linked record traversal completed successfully.",
            "data": {"links": link_data},
        }

    if operation == "create_linked_record":
        link_field_name = _canonical_field_name(payload.get("link_field_name"), table_meta)
        link_meta = _field_meta(link_field_name, table_meta)
        if str(link_meta.get("field_type") or "").strip() != "multipleRecordLinks":
            return {"status": "error", "message": "The requested link field is not a multipleRecordLinks field."}
        linked_table = _resolve_linked_table(base_meta, link_meta.get("linked_table_id"))
        linked_table_name = str(linked_table.get("table_name") or "").strip()
        if not linked_table_name:
            return {"status": "error", "message": "Linked table metadata is unavailable for the requested field."}
        linked_fields_payload = payload.get("linked_record_fields")
        if not isinstance(linked_fields_payload, dict) or not linked_fields_payload:
            return {"status": "error", "message": "linked_record_fields must be a non-empty object."}
        created = _create_record(config, linked_table_name, linked_fields_payload)
        source_fields = (record.get("fields") or {}) if isinstance(record, dict) else {}
        existing_links = source_fields.get(link_field_name) if isinstance(source_fields.get(link_field_name), list) else []
        updated_links = [str(item).strip() for item in existing_links if str(item).strip()]
        updated_links.append(str(created.get("id") or "").strip())
        _patch_record_fields(config, str(record.get("id") or "").strip(), {link_field_name: updated_links})
        return {
            "status": "success",
            "message": "Linked record created and attached to the booking successfully.",
            "data": {
                "source_record_id": str(record.get("id") or "").strip(),
                "link_field_name": link_field_name,
                "linked_table_name": linked_table_name,
                "created_record_id": str(created.get("id") or "").strip(),
            },
        }

    return {
        "status": "error",
        "message": f"Unsupported operation '{operation}'.",
    }
