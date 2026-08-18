"""
Dashboard-managed booking-platform settings (Viator, GYG, Headout, Tiqets, ...).

Persisted in booking_platforms.json. Viator connection fields also sync into
config.json viator_supplier so the Supplier API picks them up immediately.
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
SECRET_KEYS = ("api_key", "api_key_sandbox", "api_key_production")

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
        "ingest_modes": ["email", "portal"],
        "has_supplier_api": False,
        "description": "Bookings arrive by email and are upserted into Airtable by Booking Nr. (GYG...).",
        "description_ar": "الحجوزات تصل بالإيميل وتُحفظ في Airtable برقم GYG.",
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


def get_all_platform_settings() -> dict:
    stored = _load_raw().get("platforms") or {}
    out = {}
    for meta in PLATFORM_CATALOG:
        pid = meta["id"]
        merged = _default_platform_settings(pid)
        if isinstance(stored.get(pid), dict):
            merged.update(stored[pid])
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


def save_platform_settings(platform_id: str, incoming: dict) -> dict:
    allowed = {p["id"] for p in PLATFORM_CATALOG}
    if platform_id not in allowed:
        raise ValueError(f"Unknown platform: {platform_id}")
    with _LOCK:
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
            try:
                merged["supplier_id"] = int(incoming.get("supplier_id") or 0)
            except (TypeError, ValueError):
                merged["supplier_id"] = 0
        platforms[platform_id] = merged
        _save_raw(data)
        if platform_id == "viator":
            _sync_viator_into_config_json(merged)
        return merged


def _viator_health() -> dict:
    try:
        from viator_supplier_api import get_service
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


def register_booking_platforms_routes(app, agent=None):
    @app.route("/api/booking_platforms", methods=["GET", "OPTIONS"])
    def api_booking_platforms_get():
        if request.method == "OPTIONS":
            return jsonify({"status": "ok"}), 200
        try:
            settings = get_all_platform_settings()
            products = load_viator_products()
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
                    "health": _viator_health(),
                    "products": products.get("products") or [],
                    "currency": products.get("currency") or "USD",
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
            saved = save_platform_settings(platform_id, body.get("settings") or {})
            products = None
            if platform_id == "viator" and isinstance(body.get("products"), list):
                products = save_viator_products(body.get("products") or [], saved.get("currency") or "USD")
                _reload_viator_runtime()
            elif platform_id == "viator":
                _reload_viator_runtime()
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
