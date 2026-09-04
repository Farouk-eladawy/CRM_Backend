# -*- coding: utf-8 -*-
"""Company / tenant helpers for dashboard isolation."""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone

DEFAULT_COMPANY_ID = "fts"
PRIMARY_ADMIN_USERNAME = "admin"
COMPANIES_SETTING_KEY = "dashboard_companies"

NEW_COMPANY_ALLOWED_TABS = [
    "dashboard",
    "inbox",
    "customers",
    "fts_ai_operation",
    "religious_operation",
    "religious_wa_campaigns",
    "transport_operation",
]


def empty_connections():
    return {
        "baserowMainUrl": "",
        "baserowReligiousUrl": "",
        "transportUrl": "",
        "religiousWaPhoneNumberId": "",
        "religiousWaDisplay": "",
    }


def normalize_company_id(value) -> str:
    cid = str(value or "").strip()
    return cid or DEFAULT_COMPANY_ID


def is_default_company(company_id) -> bool:
    return normalize_company_id(company_id) == DEFAULT_COMPANY_ID


def coerce_bool(value, default=False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off", ""):
        return False
    return default


def is_primary_admin(user_obj) -> bool:
    if not isinstance(user_obj, dict):
        return False
    return (
        str(user_obj.get("username") or "").strip().lower() == PRIMARY_ADMIN_USERNAME
        and str(user_obj.get("role") or "").strip().lower() == "admin"
    )


def default_create_with_pi_enabled(company_id=None) -> bool:
    # Paid add-on: closed until Admin Manager enables it for the company.
    return False


def user_company_id(user_obj) -> str:
    if not isinstance(user_obj, dict):
        return DEFAULT_COMPANY_ID
    return normalize_company_id(user_obj.get("companyId") or user_obj.get("company_id"))


def new_company_id() -> str:
    return "co_" + secrets.token_hex(8)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_json(raw, fallback):
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed
        except Exception:
            return fallback
    return fallback if raw is None else fallback


def load_dashboard_users():
    import chat_db

    raw = chat_db.get_setting("dashboard_users")
    users = _parse_json(raw, [])
    return users if isinstance(users, list) else []


def find_dashboard_user(username=None, user_id=None):
    uname = str(username or "").strip().lower()
    uid = str(user_id or "").strip()
    for item in load_dashboard_users():
        if not isinstance(item, dict):
            continue
        if uname and str(item.get("username") or "").strip().lower() == uname:
            return item
        if uid and (str(item.get("id") or "").strip() == uid or str(item.get("username") or "").strip() == uid):
            return item
    return None


def resolve_company_id(username=None, user_id=None, fallback=DEFAULT_COMPANY_ID) -> str:
    user = find_dashboard_user(username=username, user_id=user_id)
    if user:
        return user_company_id(user)
    return normalize_company_id(fallback)


def sanitize_connections(raw, existing=None) -> dict:
    src = raw if isinstance(raw, dict) else {}
    out = empty_connections()
    if isinstance(existing, dict):
        for key in out:
            out[key] = str(existing.get(key) or "").strip()
    for key in out:
        if key in src:
            out[key] = str(src.get(key) or "").strip()
    out["baserowMainUrl"] = sanitize_public_url(out.get("baserowMainUrl"))
    out["baserowReligiousUrl"] = sanitize_public_url(out.get("baserowReligiousUrl"))
    out["transportUrl"] = sanitize_public_url(out.get("transportUrl"))
    return out


def _normalize_company_record(item, previous=None) -> dict:
    src = item if isinstance(item, dict) else {}
    prev = previous if isinstance(previous, dict) else {}
    cid = str(src.get("id") or prev.get("id") or "").strip()
    if src.get("createWithPiEnabled") is None:
        if prev.get("createWithPiEnabled") is None:
            flag = default_create_with_pi_enabled(cid)
        else:
            flag = coerce_bool(prev.get("createWithPiEnabled"), default=default_create_with_pi_enabled(cid))
    else:
        flag = coerce_bool(src.get("createWithPiEnabled"), default=False)
    connections_src = src.get("connections") if "connections" in src else prev.get("connections")
    created_at = str(src.get("createdAt") or prev.get("createdAt") or "").strip() or _now_iso()
    return {
        "id": cid,
        "name": str(src.get("name") or prev.get("name") or cid).strip() or cid,
        "createdByUsername": str(src.get("createdByUsername") or prev.get("createdByUsername") or "").strip(),
        "createdAt": created_at,
        "createWithPiEnabled": flag,
        "connections": sanitize_connections(connections_src),
    }


def default_fts_company():
    return {
        "id": DEFAULT_COMPANY_ID,
        "name": "FTS Travels",
        "createdByUsername": "admin",
        "createdAt": _now_iso(),
        "createWithPiEnabled": False,
        "connections": empty_connections(),
    }


def public_company(company) -> dict:
    item = company if isinstance(company, dict) else default_fts_company()
    cid = str(item.get("id") or DEFAULT_COMPANY_ID)
    return {
        "id": cid,
        "name": str(item.get("name") or cid),
        "createdByUsername": str(item.get("createdByUsername") or ""),
        "createdAt": str(item.get("createdAt") or ""),
        "createWithPiEnabled": bool(item.get("createWithPiEnabled")),
        "isDefaultCompany": is_default_company(cid),
        "connections": sanitize_connections(item.get("connections")),
    }


def load_companies():
    import chat_db

    raw = chat_db.get_setting(COMPANIES_SETTING_KEY)
    companies = _parse_json(raw, [])
    if not isinstance(companies, list):
        companies = []
    cleaned = []
    seen = set()
    for item in companies:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or "").strip()
        if not cid or cid in seen:
            continue
        seen.add(cid)
        cleaned.append(_normalize_company_record(item))
    if DEFAULT_COMPANY_ID not in seen:
        cleaned.insert(0, default_fts_company())
        save_companies(cleaned)
    return cleaned


def save_companies(companies):
    import chat_db

    payload = companies if isinstance(companies, list) else []
    chat_db.set_setting(COMPANIES_SETTING_KEY, json.dumps(payload, ensure_ascii=False))
    return payload


def get_company(company_id):
    cid = normalize_company_id(company_id)
    for item in load_companies():
        if item.get("id") == cid:
            return item
    if cid == DEFAULT_COMPANY_ID:
        return default_fts_company()
    return None


def upsert_company(company):
    if not isinstance(company, dict):
        raise ValueError("company must be an object")
    cid = str(company.get("id") or "").strip()
    if not cid:
        raise ValueError("company id is required")
    companies = load_companies()
    found = False
    next_item = None
    for idx, item in enumerate(companies):
        if item.get("id") == cid:
            next_item = _normalize_company_record(company, previous=item)
            companies[idx] = next_item
            found = True
            break
    if not found:
        next_item = _normalize_company_record(company)
        companies.append(next_item)
    save_companies(companies)
    return next_item


def create_company(name, created_by_username=""):
    company_name = str(name or "").strip() or "New Company"
    item = {
        "id": new_company_id(),
        "name": company_name,
        "createdByUsername": str(created_by_username or "").strip(),
        "createdAt": _now_iso(),
        "createWithPiEnabled": False,
        "connections": empty_connections(),
    }
    return upsert_company(item)


def get_connections(company_id) -> dict:
    company = get_company(company_id) or default_fts_company()
    return sanitize_connections(company.get("connections"))


def save_connections(company_id, connections):
    company = get_company(company_id)
    if not company:
        raise ValueError("company not found")
    company["connections"] = sanitize_connections(connections, existing=company.get("connections"))
    return upsert_company(company)


def is_create_with_pi_enabled(company_id) -> bool:
    company = get_company(company_id)
    if not company:
        return False
    return bool(company.get("createWithPiEnabled"))


def set_create_with_pi_enabled(company_id, enabled) -> dict:
    company = get_company(company_id)
    if not company:
        raise ValueError("company not found")
    company["createWithPiEnabled"] = coerce_bool(enabled, default=False)
    return upsert_company(company)


def list_public_companies():
    return [public_company(item) for item in load_companies()]


COMPANY_SCOPED_SETTING_KEYS = frozenset({
    "dashboard_general_settings",
    "dashboard_channel_settings",
    "facebook_templates",
    "whatsapp_internal_templates",
    "internal_whatsapp_notifications_config",
    "auto_reply_settings",
    "booking_platforms",
    "dashboard_company_filters",
})


def scoped_setting_key(key, company_id) -> str:
    base = str(key or "").strip()
    if not base:
        return base
    cid = normalize_company_id(company_id)
    if is_default_company(cid):
        return base
    suffix = f"__{cid}"
    if base.endswith(suffix):
        return base
    return f"{base}{suffix}"


def is_company_scoped_setting_key(key) -> bool:
    return str(key or "").strip() in COMPANY_SCOPED_SETTING_KEYS


def channel_settings_key(company_id) -> str:
    return scoped_setting_key("dashboard_channel_settings", company_id)


def _iter_phone_ids_from_channel_settings(settings):
    if not isinstance(settings, dict):
        return
    accounts = settings.get("whatsappAccounts")
    if isinstance(accounts, list):
        for acc in accounts:
            if not isinstance(acc, dict):
                continue
            for key in ("phoneNumberId", "phone_number_id", "id"):
                val = str(acc.get(key) or "").strip()
                if val:
                    yield val
    wa = settings.get("whatsapp")
    if isinstance(wa, dict):
        val = str(wa.get("phoneNumberId") or wa.get("phone_number_id") or "").strip()
        if val:
            yield val


def _iter_email_ids_from_channel_settings(settings):
    if not isinstance(settings, dict):
        return
    accounts = settings.get("emailAccounts")
    if isinstance(accounts, list):
        for acc in accounts:
            if not isinstance(acc, dict):
                continue
            for key in ("id", "email", "address"):
                val = str(acc.get(key) or "").strip().lower()
                if val:
                    yield val


def lookup_company_id_for_phone(phone_number_id) -> str:
    pid = str(phone_number_id or "").strip()
    if not pid:
        return DEFAULT_COMPANY_ID
    import chat_db

    for company in load_companies():
        cid = company.get("id") or DEFAULT_COMPANY_ID
        conn = sanitize_connections(company.get("connections"))
        if conn.get("religiousWaPhoneNumberId") == pid:
            return cid
        raw = chat_db.get_setting(channel_settings_key(cid))
        settings = _parse_json(raw, {})
        if not isinstance(settings, dict):
            settings = {}
        for candidate in _iter_phone_ids_from_channel_settings(settings):
            if candidate == pid:
                return cid
    return DEFAULT_COMPANY_ID


def lookup_company_id_for_email_account(email_account_id) -> str:
    needle = str(email_account_id or "").strip().lower()
    if not needle:
        return DEFAULT_COMPANY_ID
    import chat_db

    for company in load_companies():
        cid = company.get("id") or DEFAULT_COMPANY_ID
        raw = chat_db.get_setting(channel_settings_key(cid))
        settings = _parse_json(raw, {})
        if not isinstance(settings, dict):
            settings = {}
        for candidate in _iter_email_ids_from_channel_settings(settings):
            if candidate == needle:
                return cid
    return DEFAULT_COMPANY_ID


def stamp_user_company(user_obj, company_id):
    if not isinstance(user_obj, dict):
        return user_obj
    user_obj["companyId"] = normalize_company_id(company_id)
    return user_obj


_SAFE_URL_RE = re.compile(r"^https?://", re.I)
_BLOCKED_URL_RE = re.compile(r"^(javascript|data|vbscript|file|about):", re.I)
_HOST_URL_RE = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?::\d{1,5})?(?:[/?#].*)?$",
    re.I,
)
_LOCAL_URL_RE = re.compile(r"^(localhost|127\.0\.0\.1)(?::\d{1,5})?(?:[/?#].*)?$", re.I)


def sanitize_public_url(value) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    if _BLOCKED_URL_RE.match(url):
        return ""
    if url.startswith("//"):
        url = "https:" + url
    elif not _SAFE_URL_RE.match(url):
        if _HOST_URL_RE.match(url) or _LOCAL_URL_RE.match(url):
            url = "https://" + url
        else:
            return ""
    if not _SAFE_URL_RE.match(url):
        return ""
    return url
