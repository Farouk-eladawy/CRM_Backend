"""
Dashboard-managed booking-platform settings (Viator, GYG, Headout, Tiqets, ...).

Persisted in booking_platforms.json. Viator / GYG / Tiqets connection fields also
sync into config.json (*_supplier sections) so supplier APIs pick them up after restart.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from copy import deepcopy
from typing import Any, Optional

from flask import jsonify, request

try:
    from fts_paths import SCRIPT_DIR, get_data_path
except Exception:  # pragma: no cover
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

    def get_data_path(filename):
        return os.path.join(SCRIPT_DIR, filename)


LOGGER = logging.getLogger(__name__)
_LOCK = threading.Lock()
PLATFORMS_FILE = "booking_platforms.json"
SECRET_KEYS = (
    "api_key", "api_key_sandbox", "api_key_production",
    "basic_pass", "basic_pass_sandbox", "basic_pass_production",
)

PLATFORM_CATALOG = [
    {
        "id": "viator",
        "name": "Viator",
        "name_ar": "فاييتور",
        "agency": "Viator",
        "ingest_modes": ["api", "email", "portal"],
        "has_supplier_api": True,
        "description": "Supplier API for live availability, bookings, amendments, and cancellations.",
        "description_ar": "واجهة المورد: توافر لحظي، حجوزات، تعديل، وإلغاء.",
    },
    {
        "id": "getyourguide",
        "name": "GetYourGuide",
        "name_ar": "جيت يور جايد",
        "agency": "GetYourGuide",
        "ingest_modes": ["api", "email", "portal"],
        "has_supplier_api": True,
        "description": "Supplier-side API on /gyg/1 for availability, reserve, booking, and cancel. Email remains fallback.",
        "description_ar": "واجهة المورد على /gyg/1 للتوافر والحجز والإلغاء. الإيميل يبقى احتياطي.",
    },
    {
        "id": "headout",
        "name": "Headout",
        "name_ar": "هيد آوت",
        "agency": "Headout",
        "ingest_modes": ["email", "portal"],
        "has_supplier_api": False,
        "description": "Headout booking/cancellation emails. bookings@headout.com system mail is ignored.",
        "description_ar": "إيميلات حجوزات وإلغاء Headout. بريد النظام bookings@headout.com يُتجاهل.",
    },
    {
        "id": "tiqets",
        "name": "Tiqets",
        "name_ar": "تيكتس",
        "agency": "Tiqets",
        "ingest_modes": ["api", "email"],
        "has_supplier_api": True,
        "description": "Tiqets reservation API on /v2 (catalog, availability, booking, cancel).",
        "description_ar": "واجهة Tiqets على /v2 (كتالوج، توافر، حجز، إلغاء).",
    },
    {
        "id": "expedia",
        "name": "Expedia",
        "name_ar": "إكسبيديا",
        "agency": "Expedia",
        "ingest_modes": ["email", "portal", "manual"],
        "has_supplier_api": False,
        "description": "Expedia / Vrbo style bookings, currently email or manual ops entry.",
        "description_ar": "حجوزات Expedia حالياً عبر الإيميل أو الإدخال اليدوي.",
    },
    {
        "id": "civitatis",
        "name": "Civitatis",
        "name_ar": "سيفيتاتيس",
        "agency": "Civitatis",
        "ingest_modes": ["email", "portal", "manual"],
        "has_supplier_api": False,
        "description": "Civitatis bookings via email or manual Airtable entry.",
        "description_ar": "حجوزات Civitatis عبر الإيميل أو الإدخال اليدوي.",
    },
    {
        "id": "musement",
        "name": "Musement",
        "name_ar": "ميوزمنت",
        "agency": "Musement",
        "ingest_modes": ["email", "portal", "manual"],
        "has_supplier_api": False,
        "description": "Musement bookings via email or manual Airtable entry.",
        "description_ar": "حجوزات Musement عبر الإيميل أو الإدخال اليدوي.",
    },
    {
        "id": "direct",
        "name": "FTS Direct",
        "name_ar": "حجز مباشر",
        "agency": "FTS Travels",
        "ingest_modes": ["manual", "api"],
        "has_supplier_api": False,
        "description": "Direct website / WhatsApp / sales bookings created in the ops board.",
        "description_ar": "حجوزات الموقع وواتساب والمبيعات المباشرة من لوحة التشغيل.",
    },
]


def _default_platform_settings(platform_id: str) -> dict:
    meta = next((p for p in PLATFORM_CATALOG if p["id"] == platform_id), None) or {}
    base = {
        "enabled": platform_id in ("viator", "getyourguide", "headout", "tiqets", "direct"),
        "ingest_mode": (meta.get("ingest_modes") or ["email"])[0],
        "identifier": meta.get("agency") or platform_id,
        "routing_location": "Hurghada/Cairo",
        "notes": "",
    }
    if platform_id == "viator":
        base.update({
            "environment": "sandbox",
            "api_key": "",
            "api_key_sandbox": "",
            "api_key_production": "",
            "supplier_id": 14976,
            "reseller_id": "",
            "currency": "USD",
            "ip_allowlist": [],
            "async_airtable": True,
        })
    if platform_id == "getyourguide":
        base.update({
            "environment": "sandbox",
            "basic_user": "",
            "basic_pass": "",
            "basic_user_sandbox": "",
            "basic_pass_sandbox": "",
            "basic_user_production": "",
            "basic_pass_production": "",
            "supplier_id": "S707722",
            "currency": "EUR",
            "ip_allowlist": [],
            "async_airtable": True,
        })
    if platform_id == "tiqets":
        base.update({
            "api_key": "",
            "service_port": 5005,
        })
    return base


def _platforms_path() -> str:
    return get_data_path(PLATFORMS_FILE)


def _load_raw() -> dict:
    path = _platforms_path()
    if not os.path.isfile(path):
        return {"platforms": {}}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return {"platforms": {}}
        data.setdefault("platforms", {})
        return data
    except Exception as exc:
        LOGGER.warning("Could not read %s: %s", path, exc)
        return {"platforms": {}}


def _save_raw(data: dict) -> None:
    path = _platforms_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _mask_secret(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("••••"):
        return text
    if len(text) <= 4:
        return "••••"
    return f"••••{text[-4:]}"


def _is_masked(value: Any) -> bool:
    text = str(value or "").strip()
    return (not text) or text.startswith("••••")


def _request_company_id() -> str:
    import company_tenancy
    username = ""
    try:
        username = str(request.args.get("actor_username") or "").strip()
    except Exception:
        username = ""
    data = None
    try:
        if request.method in ("POST", "PUT", "PATCH"):
            data = request.get_json(silent=True)
    except Exception:
        data = None
    if isinstance(data, dict):
        actor = data.get("actor") if isinstance(data.get("actor"), dict) else {}
        username = username or str(actor.get("username") or data.get("actor_username") or "").strip()
    return company_tenancy.resolve_company_id(username=username or None)


def _load_company_platform_store(company_id: str) -> dict:
    import chat_db
    import company_tenancy
    raw = chat_db.get_setting(company_tenancy.scoped_setting_key("booking_platforms", company_id))
    parsed = raw
    if isinstance(parsed, str) and parsed.strip():
        try:
            parsed = json.loads(parsed)
        except Exception:
            parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    parsed.setdefault("platforms", {})
    return parsed


def _save_company_platform_store(company_id: str, data: dict) -> None:
    import chat_db
    import company_tenancy
    payload = data if isinstance(data, dict) else {"platforms": {}}
    chat_db.set_setting(
        company_tenancy.scoped_setting_key("booking_platforms", company_id),
        json.dumps(payload, ensure_ascii=False),
    )


def _merge_tiqets_config_json_defaults(settings: dict) -> dict:
    """If booking_platforms.json has no api_key, fall back to config.json tiqets_supplier."""
    merged = dict(settings)
    if str(merged.get("api_key") or "").strip():
        return merged
    config_path = os.path.join(SCRIPT_DIR, get_data_path("config.json"))
    if not os.path.isfile(config_path):
        return merged
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            section = json.load(handle).get("tiqets_supplier") or {}
        if not isinstance(section, dict):
            return merged
        for key in ("api_key", "service_port", "tickets_base_id", "audio_guide_base_url", "enabled"):
            if key in section and section.get(key) not in (None, "") and not merged.get(key):
                merged[key] = section[key]
    except Exception as exc:
        LOGGER.debug("Could not merge tiqets_supplier from config.json: %s", exc)
    return merged


def get_all_platform_settings(company_id: Optional[str] = None) -> dict:
    import company_tenancy
    if company_id and not company_tenancy.is_default_company(company_id):
        stored = _load_company_platform_store(company_id).get("platforms") or {}
    else:
        stored = _load_raw().get("platforms") or {}
    out = {}
    for meta in PLATFORM_CATALOG:
        pid = meta["id"]
        merged = _default_platform_settings(pid)
        if isinstance(stored.get(pid), dict):
            merged.update(stored[pid])
        if pid == "tiqets":
            merged = _merge_tiqets_config_json_defaults(merged)
        out[pid] = merged
    return out


def get_viator_dashboard_config() -> dict:
    settings = get_all_platform_settings().get("viator") or {}
    return {
        "enabled": bool(settings.get("enabled", True)),
        "environment": settings.get("environment") or "sandbox",
        "api_key": settings.get("api_key") or "",
        "api_key_sandbox": settings.get("api_key_sandbox") or "",
        "api_key_production": settings.get("api_key_production") or "",
        "supplier_id": settings.get("supplier_id") or 0,
        "reseller_id": settings.get("reseller_id") or "",
        "currency": settings.get("currency") or "USD",
        "ip_allowlist": settings.get("ip_allowlist") or [],
        "async_airtable": bool(settings.get("async_airtable", True)),
    }


def get_gyg_dashboard_config() -> dict:
    settings = get_all_platform_settings().get("getyourguide") or {}
    return {
        "enabled": bool(settings.get("enabled", True)),
        "environment": settings.get("environment") or "sandbox",
        "basic_user": settings.get("basic_user") or "",
        "basic_pass": settings.get("basic_pass") or "",
        "basic_user_sandbox": settings.get("basic_user_sandbox") or "",
        "basic_pass_sandbox": settings.get("basic_pass_sandbox") or "",
        "basic_user_production": settings.get("basic_user_production") or "",
        "basic_pass_production": settings.get("basic_pass_production") or "",
        "supplier_id": settings.get("supplier_id") or "S707722",
        "currency": settings.get("currency") or "EUR",
        "ip_allowlist": settings.get("ip_allowlist") or [],
        "async_airtable": bool(settings.get("async_airtable", True)),
        "products_file": "gyg_products.json",
    }


def _public_platform(settings: dict) -> dict:
    public = deepcopy(settings)
    for key in SECRET_KEYS:
        if key in public:
            public[key] = _mask_secret(public.get(key))
            public[f"{key}_configured"] = bool(str(settings.get(key) or "").strip()) and not str(settings.get(key) or "").startswith("••••")
    public["ip_allowlist_text"] = ", ".join(str(ip) for ip in (settings.get("ip_allowlist") or []) if str(ip).strip())
    return public


def load_viator_products() -> dict:
    path = get_data_path("viator_products.json")
    if not os.path.isfile(path):
        return {"currency": "USD", "products": []}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        return {"currency": "USD", "products": []}
    data.setdefault("products", [])
    return data


_PRODUCT_BOOL_FIELDS = (
    "live", "api_connected", "pilot", "pickup_offered", "private_tour",
    "accelerate_enabled", "barcode_from_reservation_system",
    "start_times_mode", "language_as_mapping_value", "special_requirements_enabled",
)
_PRODUCT_INT_FIELDS = ("daily_capacity", "cutoff_hours", "accelerate_commission_percent")
_PRODUCT_STR_FIELDS = (
    "supplier_product_name", "viator_product_code", "tour_description",
    "location", "destination_code", "destination_name", "country_code",
    "duration", "meeting_point", "timezone", "confirmation_type",
    "ticket_scope", "ticket_type", "accelerate_notes",
)
_PRODUCT_LIST_FIELDS = (
    "languages", "closed_weekdays", "blockout_dates", "inclusions",
    "exclusions", "booking_questions", "translations", "special_offers", "options",
)
_PRODUCT_DICT_FIELDS = ("age_bands",)


def _as_nonneg_int(value, default=0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return default


def save_viator_products(products: list, currency: str = "USD") -> dict:
    path = get_data_path("viator_products.json")
    current = load_viator_products()
    by_code = {
        str(p.get("supplier_product_code") or ""): p
        for p in (current.get("products") or [])
        if p.get("supplier_product_code")
    }
    for incoming in products or []:
        code = str(incoming.get("supplier_product_code") or "").strip()
        if not code or code not in by_code:
            continue
        row = by_code[code]
        for field in _PRODUCT_BOOL_FIELDS:
            if field in incoming:
                row[field] = bool(incoming.get(field))
        for field in _PRODUCT_INT_FIELDS:
            if field in incoming:
                row[field] = _as_nonneg_int(incoming.get(field), row.get(field) or 0)
        for field in _PRODUCT_STR_FIELDS:
            if field in incoming and incoming.get(field) is not None:
                row[field] = str(incoming.get(field))
        for field in _PRODUCT_LIST_FIELDS:
            if field in incoming and isinstance(incoming.get(field), list):
                row[field] = incoming.get(field)
        for field in _PRODUCT_DICT_FIELDS:
            if field in incoming and isinstance(incoming.get(field), dict):
                row[field] = incoming.get(field)
    current["currency"] = currency or current.get("currency") or "USD"
    updated = []
    for product in current.get("products") or []:
        code = str(product.get("supplier_product_code") or "")
        updated.append(by_code.get(code, product) if code else product)
    current["products"] = updated
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(current, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return current


def load_gyg_products() -> dict:
    path = get_data_path("gyg_products.json")
    if not os.path.isfile(path):
        return {
            "supplier_id": "S707722",
            "supplier_name": "FTS Travels",
            "currency": "EUR",
            "products": [],
        }
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        return {
            "supplier_id": "S707722",
            "supplier_name": "FTS Travels",
            "currency": "EUR",
            "products": [],
        }
    data.setdefault("products", [])
    data.setdefault("currency", "EUR")
    data.setdefault("supplier_id", "S707722")
    data.setdefault("supplier_name", "FTS Travels")
    return data


_GYG_API_BOOL_FIELDS = ("live", "api_connected", "pilot")
_GYG_API_INT_FIELDS = (
    "daily_capacity", "cutoff_hours", "cutoff_seconds",
    "participants_min", "participants_max",
)
_GYG_API_LIST_FIELDS = ("departure_times", "closed_weekdays", "blockout_dates")
_GYG_API_DICT_FIELDS = ("categories",)


def save_gyg_products(products: list, currency: str = "EUR") -> dict:
    """Persist Supplier-API operational fields. Marketing content stays scrape/portal-owned."""
    path = get_data_path("gyg_products.json")
    current = load_gyg_products()
    by_id = {
        str(p.get("product_id") or ""): p
        for p in (current.get("products") or [])
        if p.get("product_id")
    }
    for incoming in products or []:
        code = str(incoming.get("product_id") or "").strip()
        if not code or code not in by_id:
            continue
        row = by_id[code]
        for field in _GYG_API_BOOL_FIELDS:
            if field in incoming:
                row[field] = bool(incoming.get(field))
        for field in _GYG_API_INT_FIELDS:
            if field in incoming:
                row[field] = _as_nonneg_int(incoming.get(field), row.get(field) or 0)
        if "cutoff_hours" in incoming and "cutoff_seconds" not in incoming:
            row["cutoff_seconds"] = int(row.get("cutoff_hours") or 0) * 3600
        for field in _GYG_API_LIST_FIELDS:
            if field in incoming and isinstance(incoming.get(field), list):
                row[field] = incoming.get(field)
        for field in _GYG_API_DICT_FIELDS:
            if field in incoming and isinstance(incoming.get(field), dict):
                row[field] = incoming.get(field)
    current["currency"] = currency or current.get("currency") or "EUR"
    updated = []
    for product in current.get("products") or []:
        code = str(product.get("product_id") or "")
        updated.append(by_id.get(code, product) if code else product)
    current["products"] = updated
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(current, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return current


def _merge_secrets(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    for key, value in (incoming or {}).items():
        if key in SECRET_KEYS and _is_masked(value):
            continue
        if key == "ip_allowlist_text":
            merged["ip_allowlist"] = [
                part.strip() for part in str(value or "").replace(";", ",").split(",") if part.strip()
            ]
            continue
        if key.endswith("_configured"):
            continue
        merged[key] = value
    return merged


def _sync_viator_into_config_json(viator_settings: dict) -> None:
    config_path = os.path.join(SCRIPT_DIR, get_data_path("config.json"))
    if not os.path.isfile(config_path):
        return
    with open(config_path, "r", encoding="utf-8") as handle:
        cfg = json.load(handle)
    section = cfg.get("viator_supplier")
    if not isinstance(section, dict):
        section = {}
        cfg["viator_supplier"] = section
    for key in (
        "enabled", "environment", "api_key", "api_key_sandbox", "api_key_production",
        "supplier_id", "reseller_id", "currency", "ip_allowlist", "async_airtable",
    ):
        if key in viator_settings and viator_settings.get(key) not in (None,):
            if key in SECRET_KEYS and _is_masked(viator_settings.get(key)):
                continue
            section[key] = viator_settings[key]
    tmp = config_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, config_path)


def _sync_gyg_into_config_json(gyg_settings: dict) -> None:
    config_path = os.path.join(SCRIPT_DIR, get_data_path("config.json"))
    if not os.path.isfile(config_path):
        return
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            cfg = json.load(handle)
    except Exception as exc:
        LOGGER.warning("Could not read config.json for GYG sync: %s", exc)
        return
    if not isinstance(cfg, dict):
        return
    section = cfg.get("gyg_supplier")
    if not isinstance(section, dict):
        section = {}
        cfg["gyg_supplier"] = section
    for key in (
        "enabled", "environment", "basic_user", "basic_pass",
        "basic_user_sandbox", "basic_pass_sandbox",
        "basic_user_production", "basic_pass_production",
        "supplier_id", "currency", "ip_allowlist", "async_airtable",
    ):
        if key in gyg_settings and gyg_settings.get(key) not in (None,):
            if key in SECRET_KEYS and _is_masked(gyg_settings.get(key)):
                continue
            section[key] = gyg_settings[key]
    section["products_file"] = "gyg_products.json"
    tmp = config_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, config_path)


def _sync_tiqets_into_config_json(tiqets_settings: dict) -> None:
    config_path = os.path.join(SCRIPT_DIR, get_data_path("config.json"))
    if not os.path.isfile(config_path):
        return
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            cfg = json.load(handle)
    except Exception as exc:
        LOGGER.warning("Could not read config.json for Tiqets sync: %s", exc)
        return
    if not isinstance(cfg, dict):
        return
    section = cfg.get("tiqets_supplier")
    if not isinstance(section, dict):
        section = {}
        cfg["tiqets_supplier"] = section
    for key in (
        "enabled", "api_key", "service_port", "tickets_base_id", "audio_guide_base_url",
    ):
        if key in tiqets_settings and tiqets_settings.get(key) not in (None,):
            if key in SECRET_KEYS and _is_masked(tiqets_settings.get(key)):
                continue
            section[key] = tiqets_settings[key]
    tmp = config_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, config_path)


def save_platform_settings(platform_id: str, incoming: dict, company_id: Optional[str] = None) -> dict:
    import company_tenancy
    allowed = {p["id"] for p in PLATFORM_CATALOG}
    if platform_id not in allowed:
        raise ValueError(f"Unknown platform: {platform_id}")
    is_external = bool(company_id) and not company_tenancy.is_default_company(company_id)
    with _LOCK:
        if is_external:
            data = _load_company_platform_store(company_id)
        else:
            data = _load_raw()
        platforms = data.setdefault("platforms", {})
        current = _default_platform_settings(platform_id)
        if isinstance(platforms.get(platform_id), dict):
            current.update(platforms[platform_id])
        merged = _merge_secrets(current, incoming or {})
        if "enabled" in incoming:
            merged["enabled"] = bool(incoming.get("enabled"))
        if "ingest_mode" in incoming and incoming.get("ingest_mode"):
            merged["ingest_mode"] = str(incoming.get("ingest_mode"))
        if "supplier_id" in incoming:
            if platform_id == "getyourguide":
                merged["supplier_id"] = str(incoming.get("supplier_id") or "").strip()
            else:
                try:
                    merged["supplier_id"] = int(incoming.get("supplier_id") or 0)
                except (TypeError, ValueError):
                    merged["supplier_id"] = 0
        platforms[platform_id] = merged
        if is_external:
            _save_company_platform_store(company_id, data)
            return merged
        _save_raw(data)
        if platform_id == "viator":
            _sync_viator_into_config_json(merged)
        elif platform_id == "getyourguide":
            _sync_gyg_into_config_json(merged)
        elif platform_id == "tiqets":
            _sync_tiqets_into_config_json(merged)
        return merged


def _viator_health() -> dict:
    try:
        from viator_supplier_api import get_service
        return get_service().health()
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _gyg_health() -> dict:
    try:
        from gyg_supplier_api import get_service
        return get_service().health()
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _reload_viator_runtime() -> None:
    try:
        from viator_supplier_api import get_service
        service = get_service()
        from viator_supplier_api import load_viator_config
        service.config = load_viator_config()
        service.catalog.reload()
    except Exception as exc:
        LOGGER.warning("Could not reload Viator runtime config: %s", exc)


def _reload_gyg_runtime() -> None:
    try:
        from gyg_supplier_api import get_service, load_gyg_config
        service = get_service()
        service.config = load_gyg_config()
        service.catalog.reload()
    except Exception as exc:
        LOGGER.warning("Could not reload GYG runtime config: %s", exc)


def register_booking_platforms_routes(app, agent=None):
    @app.route("/api/booking_platforms", methods=["GET", "OPTIONS"])
    def api_booking_platforms_get():
        if request.method == "OPTIONS":
            return jsonify({"status": "ok"}), 200
        try:
            import company_tenancy
            company_id = _request_company_id()
            is_fts = company_tenancy.is_default_company(company_id)
            settings = get_all_platform_settings(None if is_fts else company_id)
            viator_products = load_viator_products() if is_fts else {"products": [], "currency": "USD"}
            gyg_products = load_gyg_products() if is_fts else {"products": [], "currency": "EUR"}
            platforms = []
            for meta in PLATFORM_CATALOG:
                pid = meta["id"]
                platforms.append({
                    **meta,
                    "settings": _public_platform(settings.get(pid) or {}),
                })
            return jsonify({
                "status": "success",
                "platforms": platforms,
                "viator": {
                    "health": _viator_health() if is_fts else {"status": "idle"},
                    "products": viator_products.get("products") or [],
                    "currency": viator_products.get("currency") or "USD",
                    "base_url": "/viator",
                    "endpoints": [
                        {"name": "Health", "method": "GET", "path": "/viator/health"},
                        {"name": "Tour List", "method": "POST", "path": "/viator/tourlist"},
                        {"name": "Availability", "method": "POST", "path": "/viator/availability"},
                        {"name": "Batch Availability", "method": "POST", "path": "/viator/batch-availability"},
                        {"name": "Booking", "method": "POST", "path": "/viator/booking"},
                        {"name": "Amendment", "method": "POST", "path": "/viator/booking-amendment"},
                        {"name": "Cancellation", "method": "POST", "path": "/viator/booking-cancellation"},
                        {"name": "Calendar v2", "method": "POST", "path": "/viator/v2/availability/calendar"},
                        {"name": "Availability Check v2", "method": "POST", "path": "/viator/v2/availability/check"},
                        {"name": "Reserve v2", "method": "POST", "path": "/viator/v2/reserve"},
                    ],
                },
                "getyourguide": {
                    "health": _gyg_health() if is_fts else {"status": "idle"},
                    "products": gyg_products.get("products") or [],
                    "currency": gyg_products.get("currency") or "EUR",
                    "supplier_id": (gyg_products.get("supplier_id") or "") if is_fts else "",
                    "supplier_name": (gyg_products.get("supplier_name") or "") if is_fts else "",
                    "base_url": "/gyg/1",
                    "endpoints": [
                        {"name": "Health", "method": "GET", "path": "/gyg/health"},
                        {"name": "Products list", "method": "GET", "path": "/gyg/1/suppliers/{supplierId}/products/"},
                        {"name": "Product details", "method": "GET", "path": "/gyg/1/products/{productId}"},
                        {"name": "Pricing categories", "method": "GET", "path": "/gyg/1/products/{productId}/pricing-categories/"},
                        {"name": "Availabilities", "method": "GET", "path": "/gyg/1/get-availabilities/"},
                        {"name": "Reserve", "method": "POST", "path": "/gyg/1/reserve/"},
                        {"name": "Cancel reservation", "method": "POST", "path": "/gyg/1/cancel-reservation/"},
                        {"name": "Book", "method": "POST", "path": "/gyg/1/book/"},
                        {"name": "Cancel booking", "method": "POST", "path": "/gyg/1/cancel-booking/"},
                    ],
                },
            }), 200
        except Exception as exc:
            LOGGER.error("booking_platforms GET failed: %s", exc, exc_info=True)
            return jsonify({"status": "error", "message": str(exc)}), 500

    @app.route("/api/booking_platforms", methods=["POST"])
    def api_booking_platforms_save():
        try:
            body = request.get_json(silent=True) or {}
            platform_id = str(body.get("platform") or "").strip().lower()
            if not platform_id:
                return jsonify({"status": "error", "message": "platform is required"}), 400
            import company_tenancy
            company_id = _request_company_id()
            is_fts = company_tenancy.is_default_company(company_id)
            saved = save_platform_settings(platform_id, body.get("settings") or {}, None if is_fts else company_id)
            products = None
            if not is_fts:
                return jsonify({
                    "status": "success",
                    "platform": platform_id,
                    "settings": _public_platform(saved),
                    "products": body.get("products") if isinstance(body.get("products"), list) else [],
                }), 200
            products = None
            if platform_id == "viator" and isinstance(body.get("products"), list):
                products = save_viator_products(body.get("products") or [], saved.get("currency") or "USD")
                _reload_viator_runtime()
            elif platform_id == "viator":
                _reload_viator_runtime()
            elif platform_id == "getyourguide" and isinstance(body.get("products"), list):
                products = save_gyg_products(body.get("products") or [], saved.get("currency") or "EUR")
                _reload_gyg_runtime()
            elif platform_id == "getyourguide":
                _reload_gyg_runtime()
            return jsonify({
                "status": "success",
                "platform": platform_id,
                "settings": _public_platform(saved),
                "products": (products or {}).get("products") if products else None,
            }), 200
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400
        except Exception as exc:
            LOGGER.error("booking_platforms POST failed: %s", exc, exc_info=True)
            return jsonify({"status": "error", "message": str(exc)}), 500
