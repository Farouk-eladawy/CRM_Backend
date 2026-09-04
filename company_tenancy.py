# -*- coding: utf-8 -*-
"""Company / tenant helpers for dashboard isolation."""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone

DEFAULT_COMPANY_ID = "fts"
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


def sanitize_connections(raw) -> dict:
    src = raw if isinstance(raw, dict) else {}
    out = empty_connections()
    for key in out:
        out[key] = str(src.get(key) or "").strip()
    return out


def default_fts_company():
    return {
        "id": DEFAULT_COMPANY_ID,
        "name": "FTS Travels",
        "createdByUsername": "admin",
        "createdAt": _now_iso(),
        "connections": empty_connections(),
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
        cleaned.append(
            {
                "id": cid,
                "name": str(item.get("name") or cid).strip() or cid,
                "createdByUsername": str(item.get("createdByUsername") or "").strip(),
                "createdAt": str(item.get("createdAt") or "").strip() or _now_iso(),
                "connections": sanitize_connections(item.get("connections")),
            }
        )
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
    next_item = {
        "id": cid,
        "name": str(company.get("name") or cid).strip() or cid,
        "createdByUsername": str(company.get("createdByUsername") or "").strip(),
        "createdAt": str(company.get("createdAt") or "").strip() or _now_iso(),
        "connections": sanitize_connections(company.get("connections")),
    }
    found = False
    for idx, item in enumerate(companies):
        if item.get("id") == cid:
            if not next_item["createdByUsername"]:
                next_item["createdByUsername"] = item.get("createdByUsername") or ""
            if not str(company.get("createdAt") or "").strip():
                next_item["createdAt"] = item.get("createdAt") or next_item["createdAt"]
            companies[idx] = next_item
            found = True
            break
    if not found:
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
    company["connections"] = sanitize_connections(connections)
    return upsert_company(company)


def channel_settings_key(company_id) -> str:
    cid = normalize_company_id(company_id)
    if cid == DEFAULT_COMPANY_ID:
        return "dashboard_channel_settings"
    return f"dashboard_channel_settings__{cid}"


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


def sanitize_public_url(value) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    if not _SAFE_URL_RE.match(url):
        return ""
    return url
