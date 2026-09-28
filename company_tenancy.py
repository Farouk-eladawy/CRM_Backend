# -*- coding: utf-8 -*-
"""Company / tenant helpers for dashboard isolation."""

from __future__ import annotations

import json
import re
import secrets
import threading
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
    "n8n_operation",
    "automation",
]


def empty_payment_settings():
    return {
        "useFtsPayment": True,
        "stripeEnabled": True,
        "wetravelEnabled": True,
        # auto = pick by currency lists; stripe/wetravel = force that provider when enabled
        "preferredProvider": "auto",
        "stripeCurrencies": ["USD"],
        "wetravelCurrencies": ["EUR", "GBP", "EGP"],
        "stripeSecretKey": "",
        "wetravelRefreshToken": "",
    }


def _sanitize_currency_list(raw, fallback):
    out = []
    seen = set()
    src = raw if isinstance(raw, (list, tuple)) else []
    for item in src:
        code = str(item or "").strip().upper()
        if not code or code in seen:
            continue
        if not re.fullmatch(r"[A-Z]{3}", code):
            continue
        seen.add(code)
        out.append(code)
    if out:
        return out
    return list(fallback or [])


def sanitize_payment_settings(raw, previous=None):
    base = empty_payment_settings()
    prev = previous if isinstance(previous, dict) else {}
    src = raw if isinstance(raw, dict) else {}
    merged = dict(base)
    for key in base:
        if key in prev:
            merged[key] = prev.get(key)
    if "useFtsPayment" in src:
        merged["useFtsPayment"] = coerce_bool(src.get("useFtsPayment"), default=True)
    if "stripeEnabled" in src:
        merged["stripeEnabled"] = coerce_bool(src.get("stripeEnabled"), default=True)
    if "wetravelEnabled" in src:
        merged["wetravelEnabled"] = coerce_bool(src.get("wetravelEnabled"), default=True)

    preferred = str(src.get("preferredProvider") if "preferredProvider" in src else merged.get("preferredProvider") or "auto").strip().lower()
    if preferred not in ("auto", "stripe", "wetravel"):
        preferred = "auto"
    merged["preferredProvider"] = preferred

    if "stripeCurrencies" in src:
        merged["stripeCurrencies"] = _sanitize_currency_list(src.get("stripeCurrencies"), ["USD"])
    else:
        merged["stripeCurrencies"] = _sanitize_currency_list(merged.get("stripeCurrencies"), ["USD"])
    if "wetravelCurrencies" in src:
        merged["wetravelCurrencies"] = _sanitize_currency_list(src.get("wetravelCurrencies"), ["EUR", "GBP", "EGP"])
    else:
        merged["wetravelCurrencies"] = _sanitize_currency_list(merged.get("wetravelCurrencies"), ["EUR", "GBP", "EGP"])

    def _secret(field):
        if field not in src or src.get(field) is None:
            return str(prev.get(field) or "")
        text = str(src.get(field) or "").strip()
        if text == "__clear__":
            return ""
        if not text:
            return str(prev.get(field) or "")
        return text

    merged["stripeSecretKey"] = _secret("stripeSecretKey")
    merged["wetravelRefreshToken"] = _secret("wetravelRefreshToken")
    merged["useFtsPayment"] = bool(merged.get("useFtsPayment", True))
    merged["stripeEnabled"] = bool(merged.get("stripeEnabled", True))
    merged["wetravelEnabled"] = bool(merged.get("wetravelEnabled", True))

    # If only one provider is enabled, force preferred to that provider.
    if merged["stripeEnabled"] and not merged["wetravelEnabled"]:
        merged["preferredProvider"] = "stripe"
    elif merged["wetravelEnabled"] and not merged["stripeEnabled"]:
        merged["preferredProvider"] = "wetravel"
    return merged


def payment_public_view(settings):
    item = sanitize_payment_settings(settings if isinstance(settings, dict) else None)
    return {
        "useFtsPayment": bool(item.get("useFtsPayment")),
        "stripeEnabled": bool(item.get("stripeEnabled")),
        "wetravelEnabled": bool(item.get("wetravelEnabled")),
        "preferredProvider": str(item.get("preferredProvider") or "auto"),
        "stripeCurrencies": list(item.get("stripeCurrencies") or ["USD"]),
        "wetravelCurrencies": list(item.get("wetravelCurrencies") or ["EUR", "GBP", "EGP"]),
        "stripeConfigured": bool(str(item.get("stripeSecretKey") or "").strip()),
        "wetravelConfigured": bool(str(item.get("wetravelRefreshToken") or "").strip()),
    }


def resolve_payment_provider(currency, settings):
    """Pick stripe or wetravel from company payment settings + invoice currency."""
    item = sanitize_payment_settings(settings if isinstance(settings, dict) else None)
    cur_raw = str(currency or "").strip().upper()
    # Normalize to a single ISO code (handles "EUR / USD", "€", lists-as-text, etc.)
    cur = ""
    for code in ("USD", "EUR", "GBP", "EGP"):
        if re.search(rf"\b{re.escape(code)}\b", cur_raw) or code == cur_raw:
            cur = code
            break
    if not cur:
        m = re.search(r"([A-Z]{3})", cur_raw)
        cur = m.group(1) if m else cur_raw
    preferred = str(item.get("preferredProvider") or "auto").strip().lower()
    stripe_on = bool(item.get("stripeEnabled"))
    wetravel_on = bool(item.get("wetravelEnabled"))
    stripe_curs = [str(x).upper() for x in (item.get("stripeCurrencies") or ["USD"])]
    wetravel_curs = [str(x).upper() for x in (item.get("wetravelCurrencies") or ["EUR", "GBP", "EGP"])]

    def _currency_matches(codes):
        if not cur:
            return False
        return cur in {str(code).upper() for code in (codes or []) if str(code or "").strip()}

    # Forced preferred only when that provider actually supports the currency
    # (or when the other provider is off / does not match).
    if preferred == "stripe" and stripe_on:
        if _currency_matches(stripe_curs) or not (wetravel_on and _currency_matches(wetravel_curs)):
            return "stripe"
    if preferred == "wetravel" and wetravel_on:
        if _currency_matches(wetravel_curs) or not (stripe_on and _currency_matches(stripe_curs)):
            return "wetravel"

    # auto: match currency lists exactly
    stripe_match = _currency_matches(stripe_curs)
    wetravel_match = _currency_matches(wetravel_curs)

    if stripe_match and stripe_on and not wetravel_match:
        return "stripe"
    if wetravel_match and wetravel_on and not stripe_match:
        return "wetravel"
    if stripe_match and stripe_on:
        return "stripe"
    if wetravel_match and wetravel_on:
        return "wetravel"
    if stripe_on and not wetravel_on:
        return "stripe"
    if wetravel_on and not stripe_on:
        return "wetravel"
    if stripe_on:
        return "stripe"
    return "wetravel"


def payment_settings(company_id=None):
    company = get_company(company_id) or {}
    settings = sanitize_payment_settings(company.get("payment"))
    # FTS is the shared payment account itself — always "use FTS path".
    if is_default_company(company_id):
        settings["useFtsPayment"] = True
    return settings


def empty_connections():
    return {
        "baserowMainUrl": "",
        "baserowReligiousUrl": "",
        "transportUrl": "",
        "n8nUrl": "",
        "religiousWaPhoneNumberId": "",
        "religiousWaDisplay": "",
        # Optional white-label hooks host (no FTS brand). Example: https://hooks.acme-travel.com
        "webhookPublicBase": "",
        # Company bookings live in their own Airtable table. Empty means "not connected".
        "airtableBaseId": "",
        "airtableBookingsTable": "",
        # Per-company Airtable personal access token. Empty = not connected for that company.
        "airtableApiKey": "",
        # Secret for Make/n8n sends on this company's hook URL. Never shared across companies.
        "outboundApiKey": "",
    }


def _is_secret_placeholder(value) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if text in ("__unchanged__", "__KEEP__", "unchanged"):
        return True
    if text.startswith("••••") or text.startswith("****"):
        return True
    if "••••" in text or "****" in text:
        return True
    return False


def mask_secret(value) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "••••••••"
    return f"{text[:4]}••••{text[-4:]}"

# Nile Crystal bookings share the main Airtable base, in table Nile_Crystal_Booking.
NILE_CRYSTAL_AIRTABLE_BASE_ID = "appTp5YgSp9DV2HYc"
NILE_CRYSTAL_BOOKINGS_TABLE = "Nile_Crystal_Booking"

_booking_ctx = threading.local()


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
        if key not in src:
            continue
        val = str(src.get(key) or "").strip()
        # Never wipe a stored Airtable token with an empty or masked UI value.
        if key in ("airtableApiKey", "outboundApiKey") and _is_secret_placeholder(val):
            continue
        out[key] = val
    out["baserowMainUrl"] = sanitize_public_url(out.get("baserowMainUrl"))
    out["baserowReligiousUrl"] = sanitize_public_url(out.get("baserowReligiousUrl"))
    out["transportUrl"] = sanitize_public_url(out.get("transportUrl"))
    out["n8nUrl"] = sanitize_public_url(out.get("n8nUrl"))
    out["webhookPublicBase"] = sanitize_public_url(out.get("webhookPublicBase")).rstrip("/")
    return out


def connections_public_view(connections) -> dict:
    """Safe copy for API/UI: mask Airtable API key, expose configured flag."""
    out = sanitize_connections(connections)
    key = str(out.get("airtableApiKey") or "").strip()
    out["airtableApiKeyConfigured"] = bool(key)
    out["airtableApiKey"] = mask_secret(key) if key else ""
    send_key = str(out.get("outboundApiKey") or "").strip()
    out["outboundApiKeyConfigured"] = bool(send_key)
    out["outboundApiKey"] = mask_secret(send_key) if send_key else ""
    return out


def company_airtable_api_key(company_id) -> str:
    """Return this company's stored Airtable token only (never another tenant's)."""
    if is_default_company(company_id):
        return ""
    conn = get_connections(company_id)
    return str(conn.get("airtableApiKey") or "").strip()


def normalize_public_slug(value, fallback="") -> str:
    raw = str(value or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", raw)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if not s:
        fb = re.sub(r"[^a-z0-9]+", "-", str(fallback or "").strip().lower())
        fb = re.sub(r"-{2,}", "-", fb).strip("-")
        s = fb
    if not s:
        s = "company"
    # Never force the public brand token "fts" for non-default companies' fallbacks
    return s[:64]


def ensure_unique_public_slug(desired, company_id=None, companies=None) -> str:
    cid = normalize_company_id(company_id) if company_id else ""
    base = normalize_public_slug(desired, fallback=cid or "company") or (cid[:64] if cid else "company")
    # Avoid generic collisions for non-latin company names
    if base in ("company", "fts") and cid and not is_default_company(cid):
        base = normalize_public_slug(cid) or cid[:64]
    rows = companies if isinstance(companies, list) else load_companies()
    taken = set()
    for item in rows:
        if not isinstance(item, dict):
            continue
        other_id = normalize_company_id(item.get("id"))
        if cid and other_id == cid:
            continue
        taken.add(normalize_public_slug(item.get("publicSlug") or item.get("name") or other_id))
    if base not in taken:
        return base
    for i in range(2, 1000):
        cand = f"{base}-{i}"[:64]
        if cand not in taken:
            return cand
    return f"{base}-{secrets.token_hex(3)}"


def find_company_by_public_slug(slug):
    needle = normalize_public_slug(slug)
    if not needle:
        return None
    for item in load_companies():
        if normalize_public_slug(item.get("publicSlug") or item.get("name") or item.get("id")) == needle:
            return item
    return None


def company_public_slug(company_or_id) -> str:
    if isinstance(company_or_id, dict):
        company = company_or_id
    else:
        company = get_company(company_or_id) or default_fts_company()
    return normalize_public_slug(company.get("publicSlug") or company.get("name") or company.get("id"))


HOOKS_PUBLIC_BASE_SETTING_KEY = "automation_hooks_public_base"
# Internal API hosts that must NEVER be shown as the public webhook URL.
INTERNAL_API_HOST_MARKERS = (
    "api.ftstravels.com",
    "localhost",
    "127.0.0.1",
)


def get_hooks_public_base(fallback="") -> str:
    """
    Public gateway host for webhooks (hides api.ftstravels.com).
    Priority: env WEBHOOK_PUBLIC_BASE / HOOKS_PUBLIC_BASE → setting → fallback (if not internal).
    """
    import os

    for key in ("WEBHOOK_PUBLIC_BASE", "HOOKS_PUBLIC_BASE"):
        env_v = sanitize_public_url(os.environ.get(key) or "").rstrip("/")
        if env_v:
            return env_v
    try:
        import chat_db

        raw = chat_db.get_setting(HOOKS_PUBLIC_BASE_SETTING_KEY)
        if isinstance(raw, dict):
            raw = raw.get("url") or raw.get("base") or ""
        stored = sanitize_public_url(raw).rstrip("/")
        if stored:
            return stored
    except Exception:
        pass
    fb = sanitize_public_url(fallback).rstrip("/")
    if fb.endswith("/api"):
        fb = fb[:-4]
    # Never advertise the internal API host as the "public" webhook base
    low = fb.lower()
    if any(m in low for m in INTERNAL_API_HOST_MARKERS):
        return ""
    return fb


def set_hooks_public_base(url: str) -> str:
    import chat_db

    cleaned = sanitize_public_url(url).rstrip("/")
    chat_db.set_setting(HOOKS_PUBLIC_BASE_SETTING_KEY, cleaned)
    return cleaned


def is_internal_api_host(url_or_host: str) -> bool:
    low = str(url_or_host or "").strip().lower()
    return any(m in low for m in INTERNAL_API_HOST_MARKERS)


def resolve_webhook_public_slug(company_or_id=None, username="") -> str:
    """
    Dynamic public webhook identity:
    1) registered company publicSlug / name
    2) else registered username
    """
    company = None
    if isinstance(company_or_id, dict):
        company = company_or_id
    elif company_or_id:
        company = get_company(company_or_id)
    if company:
        from_company = normalize_public_slug(
            company.get("publicSlug") or company.get("name") or company.get("id")
        )
        if from_company and from_company not in ("company",):
            return from_company
        # Non-latin company names may collapse; prefer id over generic "company"
        cid = normalize_company_id(company.get("id"))
        if cid and not is_default_company(cid):
            from_id = normalize_public_slug(cid)
            if from_id:
                return from_id
        if from_company:
            return from_company
    from_user = normalize_public_slug(username)
    return from_user or "company"


def company_webhook_public_base(company_or_id, fallback_api_base="", username="") -> str:
    """
    Host shown to end users for webhooks.
    Never returns api.ftstravels.com — use company override or global hooks gateway.
    """
    if isinstance(company_or_id, dict):
        company = company_or_id
    else:
        company = get_company(company_or_id) or default_fts_company()
    conns = sanitize_connections(company.get("connections"))
    custom = str(conns.get("webhookPublicBase") or "").strip().rstrip("/")
    if custom and not is_internal_api_host(custom):
        return custom
    global_base = get_hooks_public_base(fallback="")
    if global_base:
        return global_base
    # Last resort: only allow fallback if it is already a non-internal host
    fb = get_hooks_public_base(fallback=fallback_api_base)
    return fb


def list_companies_admin_view():
    """Companies list with membership counts for Admin Manager UI."""
    users = load_dashboard_users()
    out = []
    for item in list_public_companies():
        cid = normalize_company_id(item.get("id"))
        members = []
        for u in users:
            if not isinstance(u, dict):
                continue
            if user_company_id(u) != cid:
                continue
            members.append(
                {
                    "username": str(u.get("username") or ""),
                    "name": str(u.get("name") or u.get("username") or ""),
                    "role": str(u.get("role") or ""),
                }
            )
        row = dict(item)
        row["userCount"] = len(members)
        row["users"] = members
        row["hooksPublicBase"] = company_webhook_public_base(item)
        out.append(row)
    return out


def build_opaque_webhook_url(token: str, company_or_id=None, fallback_api_base="", username="") -> str:
    """Public URL that does not reveal api.ftstravels.com or internal path structure."""
    tok = str(token or "").strip()
    if not tok:
        return ""
    base = company_webhook_public_base(company_or_id, fallback_api_base=fallback_api_base, username=username)
    if not base:
        return ""
    return f"{base}/h/{tok}"


def build_company_webhook_url(company_or_id, owner, slug, fallback_api_base="", username="", token="") -> str:
    """
    Prefer opaque /h/{token} on the public hooks host.
    Readable /api/hooks/... paths are internal only (not for end-user copy).
    """
    if token:
        opaque = build_opaque_webhook_url(
            token, company_or_id=company_or_id, fallback_api_base=fallback_api_base, username=username or owner
        )
        if opaque:
            return opaque
    company = company_or_id if isinstance(company_or_id, dict) else (get_company(company_or_id) or default_fts_company())
    co_slug = resolve_webhook_public_slug(company, username=username or owner)
    owner_n = re.sub(r"[^a-z0-9._-]+", "-", str(owner or "").strip().lower()).strip("-")[:64]
    slug_n = re.sub(r"[^a-z0-9_-]+", "-", str(slug or "").strip().lower()).strip("-")[:80]
    if not co_slug or not owner_n or not slug_n:
        return ""
    base = company_webhook_public_base(company, fallback_api_base=fallback_api_base, username=username or owner)
    if not base:
        return ""
    return f"{base}/api/hooks/{co_slug}/{owner_n}/{slug_n}"


def user_belongs_to_company(username=None, user_id=None, company_id=None) -> bool:
    cid = normalize_company_id(company_id)
    user = find_dashboard_user(username=username, user_id=user_id)
    if not user:
        return False
    return user_company_id(user) == cid


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
    name = str(src.get("name") or prev.get("name") or cid).strip() or cid
    # Keep stable slug when possible; uniqueness is enforced in load_companies/upsert.
    if "publicSlug" in src and src.get("publicSlug") is not None:
        public_slug = normalize_public_slug(src.get("publicSlug"), fallback=name or cid)
    elif prev.get("publicSlug"):
        public_slug = normalize_public_slug(prev.get("publicSlug"), fallback=name or cid)
    else:
        public_slug = normalize_public_slug(name or cid)
    return {
        "id": cid,
        "name": name,
        "publicSlug": public_slug,
        "createdByUsername": str(src.get("createdByUsername") or prev.get("createdByUsername") or "").strip(),
        "createdAt": created_at,
        "createWithPiEnabled": flag,
        "payment": sanitize_payment_settings(src.get("payment") if "payment" in src else None, prev.get("payment")),
        "connections": sanitize_connections(connections_src),
    }


def default_fts_company():
    return {
        "id": DEFAULT_COMPANY_ID,
        "name": "FTS Travels",
        "publicSlug": "fts-travels",
        "createdByUsername": "admin",
        "createdAt": _now_iso(),
        "createWithPiEnabled": False,
        "payment": empty_payment_settings(),
        "connections": empty_connections(),
    }


def public_company(company) -> dict:
    item = company if isinstance(company, dict) else default_fts_company()
    cid = str(item.get("id") or DEFAULT_COMPANY_ID)
    return {
        "id": cid,
        "name": str(item.get("name") or cid),
        "publicSlug": company_public_slug(item),
        "createdByUsername": str(item.get("createdByUsername") or ""),
        "createdAt": str(item.get("createdAt") or ""),
        "createWithPiEnabled": bool(item.get("createWithPiEnabled")),
        "isDefaultCompany": is_default_company(cid),
        "payment": payment_public_view(item.get("payment")),
        "connections": connections_public_view(item.get("connections")),
        "webhookPublicBase": str(connections_public_view(item.get("connections")).get("webhookPublicBase") or ""),
    }


def load_companies():
    import chat_db

    raw = chat_db.get_setting(COMPANIES_SETTING_KEY)
    companies = _parse_json(raw, [])
    if not isinstance(companies, list):
        companies = []
    cleaned = []
    seen = set()
    dirty = False
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
        dirty = True
    for idx, item in enumerate(cleaned):
        peers = cleaned[:idx] + cleaned[idx + 1 :]
        desired = item.get("publicSlug") or item.get("name") or item.get("id")
        slug = ensure_unique_public_slug(desired, company_id=item.get("id"), companies=peers)
        if slug != item.get("publicSlug"):
            item = dict(item)
            item["publicSlug"] = slug
            cleaned[idx] = item
            dirty = True
    if dirty:
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
            peers = companies[:idx] + companies[idx + 1 :]
            next_item["publicSlug"] = ensure_unique_public_slug(
                next_item.get("publicSlug") or next_item.get("name") or cid,
                company_id=cid,
                companies=peers,
            )
            companies[idx] = next_item
            found = True
            break
    if not found:
        next_item = _normalize_company_record(company)
        next_item["publicSlug"] = ensure_unique_public_slug(
            next_item.get("publicSlug") or next_item.get("name") or cid,
            company_id=cid,
            companies=companies,
        )
        companies.append(next_item)
    save_companies(companies)
    return next_item


def create_company(name, created_by_username=""):
    company_name = str(name or "").strip() or "New Company"
    cid = new_company_id()
    item = {
        "id": cid,
        "name": company_name,
        "publicSlug": ensure_unique_public_slug(company_name, company_id=cid),
        "createdByUsername": str(created_by_username or "").strip(),
        "createdAt": _now_iso(),
        "createWithPiEnabled": False,
        "payment": empty_payment_settings(),
        "connections": empty_connections(),
    }
    return upsert_company(item)


def delete_company(company_id, *, reassign_users_to=DEFAULT_COMPANY_ID):
    """
    Remove a tenant company. Default FTS company cannot be deleted.
    Linked users are moved to reassign_users_to (usually FTS).
    """
    import chat_db

    cid = normalize_company_id(company_id)
    if is_default_company(cid):
        raise ValueError("cannot_delete_default_company")
    company = get_company(cid)
    if not company:
        raise ValueError("company_not_found")

    target = normalize_company_id(reassign_users_to)
    if target == cid:
        target = DEFAULT_COMPANY_ID
    if not get_company(target) and not is_default_company(target):
        target = DEFAULT_COMPANY_ID

    users = load_dashboard_users()
    moved = 0
    next_users = []
    for u in users:
        if not isinstance(u, dict):
            continue
        row = dict(u)
        if user_company_id(row) == cid:
            row["companyId"] = target
            row["company_id"] = target
            moved += 1
        next_users.append(row)
    if moved:
        chat_db.set_setting("dashboard_users", json.dumps(next_users, ensure_ascii=False))

    companies = [c for c in load_companies() if normalize_company_id(c.get("id")) != cid]
    save_companies(companies)

    # Drop company-scoped settings keys when present
    try:
        for base_key in COMPANY_SCOPED_SETTING_KEYS:
            scoped = scoped_setting_key(base_key, cid)
            if scoped != base_key:
                try:
                    chat_db.set_setting(scoped, "")
                except Exception:
                    pass
        # Company-scoped automation app connections store
        try:
            chat_db.set_setting(f"automation_app_connections__{cid}", "")
        except Exception:
            pass
    except Exception:
        pass

    return {
        "deletedId": cid,
        "deletedName": str(company.get("name") or cid),
        "reassignedUsers": moved,
        "reassignedTo": target,
    }


def _compact_token(value) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def _looks_like_nile_crystal(*parts) -> bool:
    blob = " ".join(str(part or "") for part in parts)
    return "nilecrystal" in _compact_token(blob)


def _company_inbox_filter_ids(company_id):
    """Location filters that belong to this company, such as Nile_Crystal."""
    generic = {"", "all", "unknown", "needhelp", "operations", "trash", "transport"}
    cid = normalize_company_id(company_id)
    found = []
    try:
        import chat_db

        raw = chat_db.get_setting(scoped_setting_key("dashboard_company_filters", cid))
        parsed = _parse_json(raw, {})
        filters = parsed.get("filters") if isinstance(parsed, dict) else None
        if isinstance(filters, list):
            for item in filters:
                fid = ""
                if isinstance(item, dict):
                    fid = str(item.get("id") or item.get("label") or "").strip()
                else:
                    fid = str(item or "").strip()
                fid = re.sub(r"\s+", "_", fid)
                if fid and fid.lower() not in generic and fid not in found:
                    found.append(fid)
    except Exception:
        pass
    return found


def company_id_for_inbox_location(location):
    """Return a non-default company when a location filter belongs only to that company."""
    wanted = re.sub(r"\s+", "_", str(location or "").strip()).lower()
    generic = {
        "", "all", "unknown", "needhelp", "operations", "trash", "transport",
        "hurghada/cairo", "hurghada", "cairo", "sharm", "sales", "religious",
        "quality", "guides", "drivers",
    }
    if wanted in generic:
        return ""
    match = ""
    for company in load_companies():
        cid = company.get("id")
        if is_default_company(cid):
            continue
        owned = {re.sub(r"\s+", "_", str(item or "").strip()).lower() for item in _company_inbox_filter_ids(cid)}
        if wanted not in owned:
            continue
        if match and normalize_company_id(match) != normalize_company_id(cid):
            return ""
        match = cid
    return match or ""


def company_customer_inbox_location(company_id, preferred=""):
    """Inbox location for a company customer chat.

    A trip city such as Hurghada/Cairo is not this company's filter.
    Using it hides the chat from the company inbox, for example Nile_Crystal.
    """
    generic = {"", "all", "unknown", "needhelp", "operations"}
    preferred_s = re.sub(r"\s+", "_", str(preferred or "").strip())
    cid = normalize_company_id(company_id)
    if is_default_company(cid):
        return preferred_s or "NeedHelp"
    company_filters = _company_inbox_filter_ids(cid)
    preferred_key = preferred_s.lower()
    if preferred_s and preferred_key not in generic:
        for fid in company_filters:
            if fid.lower() == preferred_key:
                return fid
    if company_filters:
        return company_filters[0]
    company = get_company(cid) or {}
    for key in ("name", "publicSlug", "createdByUsername"):
        val = re.sub(r"\s+", "_", str(company.get(key) or "").strip())
        if val and val.lower() not in generic:
            return val
    return "NeedHelp"


def company_is_nile_crystal(company) -> bool:
    if not isinstance(company, dict):
        return False
    if _looks_like_nile_crystal(
        company.get("name"),
        company.get("publicSlug"),
        company.get("createdByUsername"),
        company.get("id"),
    ):
        return True
    cid = normalize_company_id(company.get("id"))
    if is_default_company(cid):
        return False
    try:
        for user in load_dashboard_users():
            if not isinstance(user, dict):
                continue
            if user_company_id(user) != cid:
                continue
            if _looks_like_nile_crystal(user.get("username"), user.get("name")):
                return True
    except Exception:
        return False
    return False


def apply_known_booking_defaults(company, connections) -> dict:
    """Fill Nile Crystal's bookings table when the company has not set one yet."""
    out = dict(connections or empty_connections())
    if not isinstance(company, dict) or is_default_company(company.get("id")):
        return out
    if not company_is_nile_crystal(company):
        return out
    if not str(out.get("airtableBookingsTable") or "").strip():
        out["airtableBookingsTable"] = NILE_CRYSTAL_BOOKINGS_TABLE
    if not str(out.get("airtableBaseId") or "").strip():
        out["airtableBaseId"] = NILE_CRYSTAL_AIRTABLE_BASE_ID
    return out


def get_connections(company_id) -> dict:
    company = get_company(company_id) or default_fts_company()
    return apply_known_booking_defaults(company, sanitize_connections(company.get("connections")))


def bind_booking_company(company_id, table=None, table_name=""):
    stack = getattr(_booking_ctx, "stack", None)
    if stack is None:
        stack = []
        _booking_ctx.stack = stack
    stack.append((
        getattr(_booking_ctx, "company_id", None),
        getattr(_booking_ctx, "table", None),
        getattr(_booking_ctx, "table_name", None),
    ))
    _booking_ctx.company_id = str(company_id or "").strip() or None
    _booking_ctx.table = table
    _booking_ctx.table_name = str(table_name or "").strip() or None


def unbind_booking_company():
    stack = getattr(_booking_ctx, "stack", None) or []
    if not stack:
        _booking_ctx.company_id = None
        _booking_ctx.table = None
        _booking_ctx.table_name = None
        return
    company_id, table, table_name = stack.pop()
    _booking_ctx.company_id = company_id
    _booking_ctx.table = table
    _booking_ctx.table_name = table_name


def active_booking_company_id():
    return getattr(_booking_ctx, "company_id", None)


def active_booking_table():
    return getattr(_booking_ctx, "table", None), getattr(_booking_ctx, "table_name", None)


def set_wa_override(token=None, phone_number_id=None):
    _booking_ctx.wa_access_token = str(token or "").strip() or None
    _booking_ctx.wa_phone_number_id = str(phone_number_id or "").strip() or None


def clear_wa_override():
    _booking_ctx.wa_access_token = None
    _booking_ctx.wa_phone_number_id = None


def wa_override():
    return (
        getattr(_booking_ctx, "wa_access_token", None),
        getattr(_booking_ctx, "wa_phone_number_id", None),
    )


def _iter_company_channel_settings():
    import chat_db

    for company in load_companies():
        cid = company.get("id") or DEFAULT_COMPANY_ID
        raw = chat_db.get_setting(channel_settings_key(cid))
        settings = _parse_json(raw, {})
        if not isinstance(settings, dict):
            settings = {}
        yield cid, settings


def iter_customer_whatsapp_accounts():
    for cid, settings in _iter_company_channel_settings():
        accounts = settings.get("whatsappAccounts")
        if not isinstance(accounts, list):
            continue
        for acc in accounts:
            if not isinstance(acc, dict):
                continue
            if str(acc.get("usage") or "customers").strip().lower() == "internal_notifications":
                continue
            if acc.get("enabled") is False:
                continue
            yield cid, acc


def find_customer_whatsapp_account(phone_number_id="", instance_name="", company_id=None):
    pid = str(phone_number_id or "").strip()
    inst = str(instance_name or "").strip()
    if pid.startswith("evo:"):
        inst = pid[4:].strip()
        pid = ""
    wanted_company = normalize_company_id(company_id) if company_id else ""
    fallback = None
    for cid, acc in iter_customer_whatsapp_accounts():
        if wanted_company and normalize_company_id(cid) != wanted_company:
            continue
        provider = str(acc.get("provider") or "").strip().lower()
        row = dict(acc)
        row["companyId"] = cid
        if pid and provider == "meta" and str(acc.get("phoneNumberId") or "").strip() == pid:
            return row
        if inst and provider == "evolution" and str(acc.get("instanceName") or "").strip().lower() == inst.lower():
            return row
        if wanted_company:
            if bool(acc.get("isDefault")):
                fallback = row
            elif fallback is None:
                fallback = row
    return fallback if wanted_company and not pid and not inst else None


def update_evolution_account_connection(instance_name, connection_status="", qr_data="", whatsapp_number=""):
    """Store QR / connection state on the company Evolution customer account."""
    inst = str(instance_name or "").strip()
    if not inst:
        return False
    import chat_db

    phone = re.sub(r"\D", "", str(whatsapp_number or ""))
    changed = False
    for cid, settings in _iter_company_channel_settings():
        accounts = settings.get("whatsappAccounts")
        if not isinstance(accounts, list):
            continue
        next_accounts = []
        row_changed = False
        for acc in accounts:
            if not isinstance(acc, dict):
                next_accounts.append(acc)
                continue
            row = dict(acc)
            provider = str(row.get("provider") or "").strip().lower()
            if provider == "evolution" and str(row.get("instanceName") or "").strip().lower() == inst.lower():
                if connection_status:
                    row["connectionStatus"] = connection_status
                if qr_data:
                    row["qrCodeDataUrl"] = qr_data
                elif connection_status == "connected":
                    row["qrCodeDataUrl"] = ""
                if phone:
                    row["phoneNumber"] = phone
                if connection_status == "connected":
                    row["phoneNumberId"] = f"evo:{inst}"
                row_changed = True
            next_accounts.append(row)
        if row_changed:
            settings = dict(settings)
            settings["whatsappAccounts"] = next_accounts
            chat_db.set_setting(
                channel_settings_key(cid),
                json.dumps(settings, ensure_ascii=False),
            )
            changed = True
    return changed


def company_send_api_url(company_or_id) -> str:
    """Public Make/n8n URL. Uses the company host when set, otherwise hooks.tourcare.ai."""
    if isinstance(company_or_id, dict):
        company = company_or_id
    else:
        company = get_company(company_or_id) or default_fts_company()
    base = company_webhook_public_base(company) or "https://hooks.tourcare.ai"
    slug = company_public_slug(company)
    return f"{base.rstrip('/')}/c/{slug}/send"


def ensure_outbound_api_key(company_id) -> str:
    conn = get_connections(company_id)
    key = str(conn.get("outboundApiKey") or "").strip()
    if len(key) >= 24:
        return key
    key = secrets.token_urlsafe(32)
    conn = dict(conn)
    conn["outboundApiKey"] = key
    save_connections(company_id, conn)
    return key


def rotate_outbound_api_key(company_id) -> str:
    key = secrets.token_urlsafe(32)
    conn = dict(get_connections(company_id))
    conn["outboundApiKey"] = key
    save_connections(company_id, conn)
    return key


def outbound_api_key_matches(company_id, presented) -> bool:
    expected = str(get_connections(company_id).get("outboundApiKey") or "").strip()
    given = str(presented or "").strip()
    if not expected or not given:
        return False
    return secrets.compare_digest(expected, given)


def describe_company_outbound_channels(company_id):
    """Labels only. No tokens. Used by Company Connections and the send API."""
    import chat_db

    cid = normalize_company_id(company_id)
    raw = chat_db.get_setting(channel_settings_key(cid))
    settings = _parse_json(raw, {})
    if not isinstance(settings, dict):
        settings = {}
    emails = []
    for item in settings.get("emailAccounts") or []:
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        emails.append({
            "id": str(item.get("id") or "").strip(),
            "email": str(item.get("emailAddress") or item.get("email") or "").strip(),
            "label": str(item.get("label") or item.get("emailAddress") or item.get("id") or "").strip(),
        })
    whatsapp = []
    for item in settings.get("whatsappAccounts") or []:
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        if str(item.get("usage") or "customers").strip().lower() == "internal_notifications":
            continue
        provider = str(item.get("provider") or "").strip().lower()
        phone_id = str(item.get("phoneNumberId") or "").strip()
        if provider == "evolution" and not phone_id:
            inst = str(item.get("instanceName") or "").strip()
            phone_id = f"evo:{inst}" if inst else ""
        whatsapp.append({
            "id": str(item.get("id") or phone_id).strip(),
            "label": str(item.get("label") or item.get("displayPhone") or phone_id).strip(),
            "provider": provider,
            "phoneNumberId": phone_id,
        })
    facebook = []
    for page_id in _iter_facebook_page_ids(settings):
        if normalize_company_id(lookup_company_id_for_facebook_page(page_id)) == cid:
            facebook.append({"pageId": page_id})
    internal = []
    for item in settings.get("whatsappAccounts") or []:
        if not isinstance(item, dict) or item.get("enabled") is False:
            continue
        if str(item.get("usage") or "").strip().lower() != "internal_notifications":
            continue
        label = str(item.get("label") or item.get("displayPhone") or item.get("instanceName") or "").strip()
        phone = str(item.get("displayPhone") or item.get("phone") or "").strip()
        internal.append({
            "id": str(item.get("id") or item.get("instanceName") or "").strip(),
            "label": label or phone or "Internal",
            "phone": phone,
            "connected": bool(str(item.get("instanceName") or "").strip() and str(item.get("apiKey") or "").strip()),
        })
    if is_default_company(cid) and not internal:
        raw_cfg = chat_db.get_setting("internal_whatsapp_notifications_config")
        cfg = _parse_json(raw_cfg, {})
        if isinstance(cfg, dict) and str(cfg.get("instanceName") or "").strip() and str(cfg.get("apiKey") or "").strip():
            internal.append({
                "id": "fts_internal",
                "label": "Internal alerts",
                "phone": str(cfg.get("whatsappNumber") or "").strip(),
                "connected": True,
            })
    return {"email": emails, "whatsapp": whatsapp, "facebook": facebook, "internal": internal}


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
            for key in ("id", "email", "address", "emailAddress", "label"):
                val = str(acc.get(key) or "").strip().lower()
                if val:
                    yield val


def _iter_facebook_page_ids(settings):
    if not isinstance(settings, dict):
        return
    facebook = settings.get("facebook")
    if isinstance(facebook, dict):
        for key in ("pageId", "page_id", "id"):
            val = str(facebook.get(key) or "").strip()
            if val:
                yield val
    for list_key in ("facebookPages", "messengerAccounts", "facebookAccounts"):
        items = settings.get(list_key)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("pageId", "page_id", "id"):
                val = str(item.get(key) or "").strip()
                if val:
                    yield val


def lookup_company_id_for_phone(phone_number_id) -> str:
    pid = str(phone_number_id or "").strip()
    if not pid:
        return DEFAULT_COMPANY_ID
    if pid.startswith("evo:"):
        acc = find_customer_whatsapp_account(instance_name=pid[4:])
        if acc and acc.get("companyId"):
            return normalize_company_id(acc.get("companyId"))
        return DEFAULT_COMPANY_ID
    meta_acc = find_customer_whatsapp_account(phone_number_id=pid)
    if meta_acc and meta_acc.get("companyId") and not is_default_company(meta_acc.get("companyId")):
        return normalize_company_id(meta_acc.get("companyId"))
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


def lookup_company_id_for_facebook_page(page_id) -> str:
    pid = str(page_id or "").strip()
    if not pid:
        return ""
    import chat_db

    for company in load_companies():
        cid = company.get("id") or DEFAULT_COMPANY_ID
        raw = chat_db.get_setting(channel_settings_key(cid))
        settings = _parse_json(raw, {})
        if not isinstance(settings, dict):
            settings = {}
        for candidate in _iter_facebook_page_ids(settings):
            if candidate == pid:
                return normalize_company_id(cid)
    return ""


def _bookings_target_for_company(company_id):
    cid = normalize_company_id(company_id)
    if is_default_company(cid):
        return "", ""
    conn = get_connections(cid)
    return (
        str(conn.get("airtableBaseId") or "").strip(),
        str(conn.get("airtableBookingsTable") or "").strip(),
    )


def _inbound_route(channel, company_id, receiving_id="", account=None):
    cid = normalize_company_id(company_id)
    company = get_company(cid) or {}
    base_id, table_name = _bookings_target_for_company(cid)
    acc = account if isinstance(account, dict) else {}
    return {
        "channel": channel,
        "company_id": cid,
        "company_name": str(company.get("name") or ("FTS" if is_default_company(cid) else cid)),
        "bookings_base_id": base_id,
        "bookings_table": table_name,
        "receiving_id": str(receiving_id or "").strip(),
        "account_label": str(
            acc.get("label") or acc.get("emailAddress") or acc.get("instanceName") or acc.get("phoneNumber") or ""
        ).strip(),
        "routing_location": str(acc.get("routingLocation") or "").strip(),
    }


def resolve_inbound_route(source="", receiving_id="", email_account_id="", company_id=None, known_facebook_page_ids=None):
    """Decide the connected channel, its company, and that company's bookings table.

    Channel is one of: email, whatsapp_meta, whatsapp_evolution, facebook.
    The customer's own phone or email is not used. Only the account that received
    the message is used.
    """
    source_l = str(source or "").strip().lower()
    receiving = str(receiving_id or "").strip()
    mailbox = str(email_account_id or "").strip()
    known_pages = {
        str(item or "").strip()
        for item in (known_facebook_page_ids or [])
        if str(item or "").strip()
    }
    explicit_company = str(company_id or "").strip()

    if receiving.lower().startswith("evo:") or source_l in ("whatsapp_evolution", "evolution"):
        instance = receiving[4:].strip() if receiving.lower().startswith("evo:") else receiving
        account = find_customer_whatsapp_account(instance_name=instance) if instance else None
        cid = (account or {}).get("companyId") or explicit_company or DEFAULT_COMPANY_ID
        return _inbound_route("whatsapp_evolution", cid, receiving or (f"evo:{instance}" if instance else ""), account)

    page_company = lookup_company_id_for_facebook_page(receiving) if receiving else ""
    if source_l in ("facebook", "messenger", "facebook messenger") or page_company or (
        receiving and receiving in known_pages and source_l not in ("whatsapp", "email")
    ):
        cid = page_company or explicit_company or DEFAULT_COMPANY_ID
        return _inbound_route("facebook", cid, receiving)

    if source_l == "email" or (mailbox and source_l not in ("whatsapp", "facebook", "messenger")):
        cid = lookup_company_id_for_email_account(mailbox) if mailbox else (explicit_company or DEFAULT_COMPANY_ID)
        return _inbound_route("email", cid, mailbox)

    if source_l == "whatsapp" or receiving:
        account = find_customer_whatsapp_account(phone_number_id=receiving) if receiving else None
        provider = str((account or {}).get("provider") or "").strip().lower()
        if provider == "evolution":
            instance = str((account or {}).get("instanceName") or "").strip()
            return _inbound_route(
                "whatsapp_evolution",
                (account or {}).get("companyId") or explicit_company or DEFAULT_COMPANY_ID,
                receiving or (f"evo:{instance}" if instance else ""),
                account,
            )
        if account and account.get("companyId"):
            return _inbound_route("whatsapp_meta", account.get("companyId"), receiving, account)
        cid = lookup_company_id_for_phone(receiving) if receiving else (explicit_company or DEFAULT_COMPANY_ID)
        if source_l == "whatsapp" or (receiving and not is_default_company(cid)):
            return _inbound_route("whatsapp_meta", cid, receiving, account)

    if explicit_company:
        return _inbound_route(source_l or "email", explicit_company, receiving or mailbox)
    return _inbound_route(source_l or "whatsapp_meta", DEFAULT_COMPANY_ID, receiving or mailbox)


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
