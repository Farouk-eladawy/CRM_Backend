"""
FTS Travels — partner sandbox API (Vern / new OTAs).

Public contract (matches the sample we sent Vern):
  GET  /partner/v1/health
  GET  /partner/v1/products
  POST /partner/v1/availability
  POST /partner/v1/bookings
  GET  /partner/v1/bookings/<vern_booking_id>
  GET  /partner/v1/openapi.json

Aliases under /api/partner/sandbox/... do the same thing.

Sandbox only: no Airtable, no WhatsApp, no live inventory.
Auth: Authorization: Bearer <token>  (or X-Api-Key)
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from flask import Flask, jsonify, request

try:
    from fts_paths import get_data_path, SCRIPT_DIR, ensure_data_dir
except Exception:  # pragma: no cover
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

    def get_data_path(filename):
        return os.path.join(SCRIPT_DIR, filename)

    def ensure_data_dir():
        os.makedirs(SCRIPT_DIR, exist_ok=True)


LOGGER = logging.getLogger(__name__)
CAIRO_TZ = timezone(timedelta(hours=2))
CONFIG_NAME = "partner_sandbox_config.json"
BOOKINGS_NAME = "partner_sandbox_bookings.json"

DEMO_PRODUCTS = [
    {
        "product_id": "FTS-HUR-QUAD-001",
        "name": "Quad Bike Desert Safari — Hurghada",
        "city": "Hurghada",
        "currency": "EUR",
        "cutoff_hours": 12,
        "capacity": 16,
        "price": {"adult": 45.00, "child": 30.00},
    },
    {
        "product_id": "FTS-LXR-VALLEY-001",
        "name": "Valley of the Kings Day Tour — Luxor",
        "city": "Luxor",
        "currency": "EUR",
        "cutoff_hours": 24,
        "capacity": 20,
        "price": {"adult": 85.00, "child": 45.00},
    },
    {
        "product_id": "FTS-CAI-PYRAMIDS-001",
        "name": "Giza Pyramids & Sphinx — Cairo",
        "city": "Cairo",
        "currency": "EUR",
        "cutoff_hours": 24,
        "capacity": 24,
        "price": {"adult": 55.00, "child": 30.00},
    },
]

_LOCK = threading.Lock()
_TOKEN_CACHE: Optional[str] = None
_BOOKINGS: dict[str, dict] = {}
_SEQ = 88420
_MEMORY_ONLY = False


def _config_path() -> str:
    ensure_data_dir()
    return get_data_path(CONFIG_NAME)


def _bookings_path() -> str:
    ensure_data_dir()
    return get_data_path(BOOKINGS_NAME)


def load_sandbox_token(force_reload: bool = False) -> str:
    """Env PARTNER_SANDBOX_TOKEN wins; otherwise persist a generated token."""
    global _TOKEN_CACHE
    env_token = (os.environ.get("PARTNER_SANDBOX_TOKEN") or "").strip()
    if env_token:
        _TOKEN_CACHE = env_token
        return env_token
    if _TOKEN_CACHE and not force_reload:
        return _TOKEN_CACHE
    path = _config_path()
    data: dict[str, Any] = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh) or {}
        except Exception as exc:
            LOGGER.warning("Could not read %s: %s", path, exc)
    token = str(data.get("token") or "").strip()
    if not token:
        token = secrets.token_urlsafe(32)
        data = {
            "token": token,
            "environment": "sandbox",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "note": "Share only with approved OTA partners. Rotate by deleting this file or setting PARTNER_SANDBOX_TOKEN.",
        }
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
        except Exception as exc:
            LOGGER.error("Could not write sandbox token file: %s", exc)
    _TOKEN_CACHE = token
    return token


def _load_bookings_from_disk() -> None:
    global _BOOKINGS, _SEQ
    if _MEMORY_ONLY:
        return
    path = _bookings_path()
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh) or {}
        items = raw.get("bookings") or {}
        if isinstance(items, dict):
            _BOOKINGS.update(items)
        _SEQ = int(raw.get("seq") or _SEQ)
    except Exception as exc:
        LOGGER.warning("Could not read sandbox bookings: %s", exc)


def _save_bookings_to_disk() -> None:
    if _MEMORY_ONLY:
        return
    path = _bookings_path()
    payload = {"seq": _SEQ, "bookings": _BOOKINGS, "updated_at": datetime.now(timezone.utc).isoformat()}
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
    except Exception as exc:
        LOGGER.error("Could not write sandbox bookings: %s", exc)


def _product_map() -> dict[str, dict]:
    return {p["product_id"]: p for p in DEMO_PRODUCTS}


def _extract_bearer() -> str:
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return (request.headers.get("X-Api-Key") or "").strip()


def _unauthorized():
    return jsonify({
        "status": "error",
        "code": "UNAUTHORIZED",
        "message": "Provide Authorization: Bearer <sandbox-token> or X-Api-Key.",
    }), 401


def _require_auth():
    provided = _extract_bearer()
    expected = load_sandbox_token()
    if not provided or not secrets.compare_digest(provided, expected):
        return False
    return True


def _parse_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _pax_counts(pax: Any) -> tuple[int, int]:
    if not isinstance(pax, dict):
        pax = {}
    adults = int(pax.get("adults") or 0)
    children = int(pax.get("children") or 0)
    return max(adults, 0), max(children, 0)


def _today_cairo() -> date:
    return datetime.now(CAIRO_TZ).date()


def check_availability(body: dict) -> tuple[int, dict]:
    product_id = str(body.get("product_id") or "").strip()
    trip_date = _parse_date(body.get("date"))
    adults, children = _pax_counts(body.get("pax"))
    product = _product_map().get(product_id)
    if not product:
        return 404, {
            "status": "error",
            "code": "UNKNOWN_PRODUCT",
            "available": False,
            "message": f"Unknown product_id: {product_id or '(missing)'}",
        }
    if not trip_date:
        return 400, {
            "status": "error",
            "code": "INVALID_DATE",
            "available": False,
            "message": "date must be YYYY-MM-DD",
        }
    total = adults + children
    if total < 1:
        return 400, {
            "status": "error",
            "code": "INVALID_PAX",
            "available": False,
            "message": "pax.adults + pax.children must be at least 1",
        }
    today = _today_cairo()
    cutoff_hours = int(product["cutoff_hours"])
    available = True
    reason = None
    if trip_date < today:
        available = False
        reason = "date_in_past"
    elif trip_date == today:
        available = False
        reason = "same_day_closed_in_sandbox"
    elif total > int(product["capacity"]):
        available = False
        reason = "over_capacity"
    elif (trip_date - today).days > 365:
        available = False
        reason = "too_far_ahead"

    payload = {
        "available": available,
        "product_id": product_id,
        "date": trip_date.isoformat(),
        "cutoff_hours": cutoff_hours,
        "currency": product["currency"],
        "price": product["price"],
        "sandbox": True,
    }
    if reason:
        payload["reason"] = reason
    return 200, payload


def create_booking(body: dict) -> tuple[int, dict]:
    global _SEQ
    vern_id = str(body.get("vern_booking_id") or body.get("partner_booking_id") or "").strip()
    if not vern_id:
        return 400, {
            "status": "error",
            "code": "MISSING_BOOKING_ID",
            "message": "vern_booking_id is required",
        }
    with _LOCK:
        existing = _BOOKINGS.get(vern_id)
        if existing:
            return 200, {**existing, "idempotent_replay": True}

        avail_status, avail = check_availability(body)
        if avail_status != 200 or not avail.get("available"):
            return 409 if avail_status == 200 else avail_status, {
                "status": "error",
                "code": "NOT_AVAILABLE",
                "message": "This product/date is not available in sandbox.",
                "availability": avail,
            }

        customer = body.get("customer") if isinstance(body.get("customer"), dict) else {}
        first = str(customer.get("first_name") or "").strip()
        last = str(customer.get("last_name") or "").strip()
        if not first or not last:
            return 400, {
                "status": "error",
                "code": "MISSING_CUSTOMER",
                "message": "customer.first_name and customer.last_name are required",
            }

        _SEQ += 1
        confirmation = f"FTS-TEST-{_SEQ}"
        adults, children = _pax_counts(body.get("pax"))
        record = {
            "status": "confirmed",
            "sandbox": True,
            "writes_to_airtable": False,
            "vern_booking_id": vern_id,
            "fts_confirmation": confirmation,
            "product_id": str(body.get("product_id") or "").strip(),
            "date": str(body.get("date") or "")[:10],
            "pickup_time": str(body.get("pickup_time") or "") or None,
            "hotel_name": str(body.get("hotel_name") or "") or None,
            "pax": {"adults": adults, "children": children},
            "customer": {
                "first_name": first,
                "last_name": last,
                "email": str(customer.get("email") or ""),
                "phone": str(customer.get("phone") or ""),
            },
            "voucher_note": "SANDBOX ONLY — not a live booking. Please present this confirmation at pickup (test).",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _BOOKINGS[vern_id] = record
        _save_bookings_to_disk()
        return 201, record


def get_booking(vern_id: str) -> tuple[int, dict]:
    record = _BOOKINGS.get(vern_id)
    if not record:
        return 404, {"status": "error", "code": "NOT_FOUND", "message": "Unknown vern_booking_id in sandbox"}
    return 200, record


def openapi_document() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "FTS Travels Partner Sandbox API",
            "version": "1.0.0",
            "description": (
                "Illustrative supplier sandbox. Vern (or any OTA) calls FTS. "
                "No live inventory and no Airtable writes. Align production fields to your spec later."
            ),
        },
        "servers": [{"url": "https://crm.ftstravels.com", "description": "FTS CRM (sandbox paths)"}],
        "security": [{"bearerAuth": []}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"},
            }
        },
        "paths": {
            "/partner/v1/health": {
                "get": {"summary": "Health (no auth)", "security": [], "responses": {"200": {"description": "ok"}}},
            },
            "/partner/v1/products": {
                "get": {"summary": "Demo catalog", "responses": {"200": {"description": "ok"}, "401": {"description": "auth"}}},
            },
            "/partner/v1/availability": {
                "post": {"summary": "Check availability + sample price", "responses": {"200": {"description": "ok"}}},
            },
            "/partner/v1/bookings": {
                "post": {"summary": "Create sandbox booking (idempotent on vern_booking_id)", "responses": {"201": {"description": "created"}}},
            },
        },
    }


def _json(status: int, body: dict):
    return jsonify(body), status


def register_partner_sandbox_routes(app: Flask, agent=None):
    global _MEMORY_ONLY
    if os.environ.get("PARTNER_SANDBOX_MEMORY") == "1":
        _MEMORY_ONLY = True
    _load_bookings_from_disk()
    load_sandbox_token()

    prefixes = (
        ("v1", "/partner/v1"),
        ("alias", "/api/partner/sandbox"),
    )

    def health():
        if request.method == "OPTIONS":
            return jsonify({"status": "ok"}), 200
        return jsonify({
            "status": "ok",
            "environment": "sandbox",
            "writes_to_airtable": False,
            "company": "FTS Travels",
            "auth": "Bearer token required except health and openapi",
        }), 200

    def openapi():
        if request.method == "OPTIONS":
            return jsonify({"status": "ok"}), 200
        return jsonify(openapi_document()), 200

    def products():
        if request.method == "OPTIONS":
            return jsonify({"status": "ok"}), 200
        if not _require_auth():
            return _unauthorized()
        return jsonify({"status": "success", "sandbox": True, "currency": "EUR", "products": DEMO_PRODUCTS}), 200

    def availability():
        if request.method == "OPTIONS":
            return jsonify({"status": "ok"}), 200
        if not _require_auth():
            return _unauthorized()
        body = request.get_json(silent=True) or {}
        return _json(*check_availability(body))

    def bookings_post():
        if request.method == "OPTIONS":
            return jsonify({"status": "ok"}), 200
        if not _require_auth():
            return _unauthorized()
        body = request.get_json(silent=True) or {}
        return _json(*create_booking(body))

    def bookings_get(vern_booking_id):
        if request.method == "OPTIONS":
            return jsonify({"status": "ok"}), 200
        if not _require_auth():
            return _unauthorized()
        return _json(*get_booking(vern_booking_id))

    for key, prefix in prefixes:
        app.add_url_rule(f"{prefix}/health", f"partner_sandbox_health_{key}", health, methods=["GET", "OPTIONS"])
        app.add_url_rule(f"{prefix}/openapi.json", f"partner_sandbox_openapi_{key}", openapi, methods=["GET", "OPTIONS"])
        app.add_url_rule(f"{prefix}/products", f"partner_sandbox_products_{key}", products, methods=["GET", "OPTIONS"])
        app.add_url_rule(f"{prefix}/availability", f"partner_sandbox_availability_{key}", availability, methods=["POST", "OPTIONS"])
        app.add_url_rule(f"{prefix}/bookings", f"partner_sandbox_bookings_{key}", bookings_post, methods=["POST", "OPTIONS"])
        app.add_url_rule(
            f"{prefix}/bookings/<vern_booking_id>",
            f"partner_sandbox_booking_get_{key}",
            bookings_get,
            methods=["GET", "OPTIONS"],
        )

    LOGGER.info("Partner sandbox API registered under /partner/v1")
    return app


def create_test_app(token: str = "sandbox-test-token") -> Flask:
    global _TOKEN_CACHE, _BOOKINGS, _SEQ, _MEMORY_ONLY
    os.environ["PARTNER_SANDBOX_TOKEN"] = token
    os.environ["PARTNER_SANDBOX_MEMORY"] = "1"
    _MEMORY_ONLY = True
    _TOKEN_CACHE = token
    _BOOKINGS = {}
    _SEQ = 88420
    app = Flask(__name__)
    register_partner_sandbox_routes(app)
    _BOOKINGS = {}
    _SEQ = 88420
    return app


if __name__ == "__main__":
    token = load_sandbox_token()
    print("Partner sandbox token (keep private):")
    print(token)
    print("Health: GET /partner/v1/health")
