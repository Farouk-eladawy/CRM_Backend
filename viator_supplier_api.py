"""
Viator Supplier / Reservation System API (FTS Travels).

Viator calls OUR HTTPS endpoints. This is not the Partner/Affiliate API.
All public routes live under /viator so they never collide with the Tiqets /v2 proxy.

Official contract: https://docs.viator.com/supplier-api/technical/
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone, date
from typing import Any, Optional

from flask import Blueprint, Flask, jsonify, request

try:
    from fts_paths import get_data_path, SCRIPT_DIR
except Exception:  # pragma: no cover
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

    def get_data_path(filename):
        return os.path.join(SCRIPT_DIR, filename)

try:
    from airtable_fields import FieldIds
except Exception:  # pragma: no cover
    FieldIds = None  # type: ignore


LOGGER = logging.getLogger(__name__)
HOLD_SECONDS = 15 * 60
MAX_CALENDAR_DAYS = 400
PROXY_EMAIL_MARKERS = (
    "expmessaging.tripadvisor.com",
    "expmessaging.viator.com",
    "reply.getyourguide.com",
)
AGE_BANDS = ("Adult", "Child", "Youth", "Infant", "Senior")
V2_TICKET_TYPES = ("ADULT", "CHILD", "YOUTH", "INFANT", "SENIOR")
CAPACITY_CONSUMERS = ("ADULT", "CHILD", "YOUTH", "SENIOR")

# v1 error codes (legacy Supplier API)
ERR_MALFORMED = "TGDS0001"
ERR_AUTH = "TGDS0002"
ERR_INVALID_SUPPLIER = "TGDS0011"
ERR_INVALID_PRODUCT = "TGDS0012"
ERR_INVALID_OPTION = "TGDS0013"
ERR_INVALID_RESELLER = "TGDS0015"
ERR_VALIDATION = "TGDS0020"
ERR_INVALID_DATA = "TGDS0023"
ERR_INTERNAL = "TGDS0031"
ERR_UNAVAILABLE = "TGDS0032"
ERR_TRAVELLER_MIX = "TGDS0036"

_SERVICE_LOCK = threading.Lock()
_SERVICE: Optional["ViatorSupplierService"] = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _date_range(start: date, end: date) -> list[date]:
    if end < start:
        return []
    days = (end - start).days + 1
    if days > MAX_CALENDAR_DAYS:
        end = start + timedelta(days=MAX_CALENDAR_DAYS - 1)
        days = MAX_CALENDAR_DAYS
    return [start + timedelta(days=i) for i in range(days)]


def _hhmm(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "00:00"
    parts = raw.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return f"{hour:02d}:{minute:02d}"
    except (TypeError, ValueError):
        return "00:00"


def _hhmmss(value: Any) -> str:
    hhmm = _hhmm(value)
    return f"{hhmm}:00"


def _redact(payload: Any) -> Any:
    if isinstance(payload, dict):
        out = {}
        for key, value in payload.items():
            if str(key).lower() in {"apikey", "api_key", "x-api-key"}:
                out[key] = "***REDACTED***"
            else:
                out[key] = _redact(value)
        return out
    if isinstance(payload, list):
        return [_redact(item) for item in payload]
    return payload


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_booking_ref(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.upper().startswith("BR-"):
        return "BR-" + raw[3:].strip()
    if raw.isdigit():
        return f"BR-{raw}"
    return raw


def _client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return (request.remote_addr or "").strip()


def _clean_phone(phone: Any) -> str:
    if not phone:
        return ""
    cleaned = re.sub(r"[^\d+]", "", str(phone))
    if cleaned.count("+") > 1:
        cleaned = "+" + cleaned.replace("+", "")
    return cleaned


def _is_proxy_email(email: str) -> bool:
    lowered = (email or "").lower()
    return any(marker in lowered for marker in PROXY_EMAIL_MARKERS)


def _map_location(raw: str) -> str:
    text = (raw or "").lower()
    if "ras mohamed" in text or "sharm" in text:
        return "Sharm"
    if "hurghada" in text or "makadi" in text or "el gouna" in text or "sahl hasheesh" in text:
        return "Hurghada"
    if "luxor" in text:
        return "Luxor"
    if "cairo" in text or "giza" in text:
        return "Cairo"
    if "marsa alam" in text:
        return "Marsa Alam"
    return (raw or "").split(",")[0].strip() or raw


def load_viator_config(override: Optional[dict] = None) -> dict:
    cfg: dict[str, Any] = {
        "enabled": True,
        "api_key": "",
        "api_key_sandbox": "",
        "api_key_production": "",
        "supplier_id": 0,
        "reseller_id": "",
        "environment": "sandbox",
        "currency": "USD",
        "ip_allowlist": [],
        "products_file": "viator_products.json",
        "async_airtable": True,
    }
    try:
        config_path = os.path.join(SCRIPT_DIR, get_data_path("config.json"))
        if os.path.isfile(config_path):
            with open(config_path, "r", encoding="utf-8") as handle:
                file_cfg = json.load(handle).get("viator_supplier") or {}
            if isinstance(file_cfg, dict):
                cfg.update(file_cfg)
    except Exception as exc:
        LOGGER.warning("Could not load viator_supplier config.json section: %s", exc)

    env_map = {
        "VIATOR_SUPPLIER_API_KEY": "api_key",
        "VIATOR_SUPPLIER_API_KEY_SANDBOX": "api_key_sandbox",
        "VIATOR_SUPPLIER_API_KEY_PRODUCTION": "api_key_production",
        "VIATOR_SUPPLIER_ID": "supplier_id",
        "VIATOR_RESELLER_ID": "reseller_id",
        "VIATOR_SUPPLIER_ENV": "environment",
    }
    for env_name, key in env_map.items():
        val = os.environ.get(env_name)
        if val:
            cfg[key] = int(val) if key == "supplier_id" and str(val).isdigit() else val

    if override:
        cfg.update(override)
    cfg["supplier_id"] = _as_int(cfg.get("supplier_id"), 0)
    cfg["ip_allowlist"] = [str(ip).strip() for ip in (cfg.get("ip_allowlist") or []) if str(ip).strip()]
    return cfg


def _accepted_api_keys(cfg: dict) -> set[str]:
    keys = {
        str(cfg.get("api_key") or "").strip(),
        str(cfg.get("api_key_sandbox") or "").strip(),
        str(cfg.get("api_key_production") or "").strip(),
    }
    return {k for k in keys if k}


class ProductCatalog:
    def __init__(self, products_file: str):
        self.products_file = products_file
        self.products: list[dict] = []
        self.currency = "USD"
        self.reload()

    def reload(self) -> None:
        path = self.products_file
        if not os.path.isabs(path):
            path = get_data_path(path)
        if not os.path.isfile(path):
            LOGGER.error("Viator products file missing: %s", path)
            self.products = []
            return
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        self.currency = str(raw.get("currency") or "USD")
        self.products = list(raw.get("products") or [])

    def live_products(self) -> list[dict]:
        return [p for p in self.products if p.get("live")]

    def connected_codes(self) -> list[str]:
        return [p.get("supplier_product_code") for p in self.products if p.get("api_connected")]

    def get_product(self, code: str) -> Optional[dict]:
        wanted = str(code or "").strip()
        if not wanted:
            return None
        for product in self.products:
            if product.get("supplier_product_code") == wanted:
                return product
            if product.get("viator_product_code") == wanted:
                return product
        return None

    def get_option(self, product: dict, option_code: str = "", product_option_id: str = "", departure: str = "") -> Optional[dict]:
        options = product.get("options") or []
        if product_option_id:
            for option in options:
                if option.get("product_option_id") == product_option_id:
                    return option
        if option_code:
            matches = [o for o in options if o.get("supplier_option_code") == option_code]
            if departure:
                dep = _hhmmss(departure)
                timed = [o for o in matches if _hhmmss(o.get("departure_time")) == dep]
                if timed:
                    return timed[0]
            if matches:
                return matches[0]
        if len(options) == 1:
            return options[0]
        return None

    def option_by_id(self, product_option_id: str) -> tuple[Optional[dict], Optional[dict]]:
        for product in self.products:
            option = self.get_option(product, product_option_id=product_option_id)
            if option:
                return product, option
        return None, None


class ViatorStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_data_path("viator_supplier.db")
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    booking_reference TEXT PRIMARY KEY,
                    supplier_confirmation TEXT,
                    status TEXT,
                    travel_date TEXT,
                    product_code TEXT,
                    option_code TEXT,
                    option_name TEXT,
                    departure_time TEXT,
                    lead_name TEXT,
                    traveler_names TEXT,
                    adults INTEGER DEFAULT 0,
                    children INTEGER DEFAULT 0,
                    youth INTEGER DEFAULT 0,
                    infants INTEGER DEFAULT 0,
                    seniors INTEGER DEFAULT 0,
                    total_pax INTEGER DEFAULT 0,
                    pickup_point TEXT,
                    phone TEXT,
                    email TEXT,
                    notes TEXT,
                    questions_json TEXT,
                    net_amount REAL DEFAULT 0,
                    currency TEXT,
                    location TEXT,
                    payload_json TEXT,
                    airtable_record_id TEXT,
                    hold_reference TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS holds (
                    reference TEXT PRIMARY KEY,
                    product_code TEXT,
                    option_code TEXT,
                    product_option_id TEXT,
                    travel_date TEXT,
                    start_time TEXT,
                    total_pax INTEGER DEFAULT 0,
                    tickets_json TEXT,
                    expires_at TEXT,
                    consumed INTEGER DEFAULT 0,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT,
                    request_type TEXT,
                    booking_reference TEXT,
                    status_code INTEGER,
                    request_json TEXT,
                    response_json TEXT,
                    error TEXT,
                    created_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_viator_bookings_capacity
                    ON bookings(travel_date, product_code, option_code, status);
                CREATE INDEX IF NOT EXISTS idx_viator_holds_capacity
                    ON holds(travel_date, product_code, option_code, consumed);
                """
            )
            conn.commit()

    def log_request(self, endpoint: str, request_type: str, booking_reference: str,
                    status_code: int, request_json: Any, response_json: Any, error: str = "") -> None:
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO request_logs
                    (endpoint, request_type, booking_reference, status_code, request_json, response_json, error, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        endpoint,
                        request_type,
                        booking_reference or "",
                        status_code,
                        json.dumps(_redact(request_json), ensure_ascii=False, default=str)[:20000],
                        json.dumps(_redact(response_json), ensure_ascii=False, default=str)[:20000],
                        (error or "")[:2000],
                        _now_iso(),
                    ),
                )
                conn.commit()
        except Exception as exc:
            LOGGER.warning("Failed to log Viator request: %s", exc)

    def get_booking(self, booking_reference: str) -> Optional[dict]:
        ref = _normalize_booking_ref(booking_reference)
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM bookings WHERE booking_reference = ?",
                (ref,),
            ).fetchone()
        return dict(row) if row else None

    def upsert_booking(self, record: dict) -> dict:
        ref = record["booking_reference"]
        now = _now_iso()
        record = dict(record)
        record.setdefault("created_at", now)
        record["updated_at"] = now
        columns = [
            "booking_reference", "supplier_confirmation", "status", "travel_date",
            "product_code", "option_code", "option_name", "departure_time",
            "lead_name", "traveler_names", "adults", "children", "youth",
            "infants", "seniors", "total_pax", "pickup_point", "phone", "email",
            "notes", "questions_json", "net_amount", "currency", "location",
            "payload_json", "airtable_record_id", "hold_reference",
            "created_at", "updated_at",
        ]
        placeholders = ", ".join("?" for _ in columns)
        assignments = ", ".join(f"{c}=excluded.{c}" for c in columns if c not in ("booking_reference", "created_at"))
        values = [record.get(c) for c in columns]
        with self._lock, self._connect() as conn:
            conn.execute(
                f"""
                INSERT INTO bookings ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(booking_reference) DO UPDATE SET {assignments},
                    created_at=bookings.created_at
                """,
                values,
            )
            conn.commit()
        return self.get_booking(ref) or record

    def booked_pax(self, product_code: str, travel_date: str, option_code: str = "", departure: str = "") -> int:
        sql = """
            SELECT COALESCE(SUM(adults + children + youth + seniors), 0)
            FROM bookings
            WHERE product_code = ?
              AND travel_date = ?
              AND status IN ('CONFIRMED', 'AMENDED', 'Active', 'Changed')
        """
        params: list[Any] = [product_code, travel_date]
        if option_code:
            sql += " AND option_code = ?"
            params.append(option_code)
        if departure:
            sql += " AND departure_time = ?"
            params.append(_hhmmss(departure))
        with self._lock, self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row[0] if row else 0)

    def held_pax(self, product_code: str, travel_date: str, option_code: str = "", departure: str = "") -> int:
        now = _now_iso()
        sql = """
            SELECT COALESCE(SUM(total_pax), 0)
            FROM holds
            WHERE product_code = ?
              AND travel_date = ?
              AND consumed = 0
              AND expires_at > ?
        """
        params: list[Any] = [product_code, travel_date, now]
        if option_code:
            sql += " AND option_code = ?"
            params.append(option_code)
        if departure:
            sql += " AND start_time = ?"
            params.append(_hhmm(departure))
        with self._lock, self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row[0] if row else 0)

    def create_hold(self, product_code: str, option_code: str, product_option_id: str,
                    travel_date: str, start_time: str, total_pax: int, tickets: Any) -> dict:
        reference = f"HOLD-{uuid.uuid4().hex[:12].upper()}"
        expires_at = (_now_utc() + timedelta(seconds=HOLD_SECONDS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO holds
                (reference, product_code, option_code, product_option_id, travel_date, start_time,
                 total_pax, tickets_json, expires_at, consumed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    reference, product_code, option_code, product_option_id, travel_date,
                    _hhmm(start_time), total_pax, json.dumps(tickets or []), expires_at, _now_iso(),
                ),
            )
            conn.commit()
        return {"reference": reference, "expires_at": expires_at, "total_pax": total_pax}

    def consume_hold(self, reference: str) -> Optional[dict]:
        if not reference:
            return None
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM holds WHERE reference = ?", (reference,)).fetchone()
            if not row:
                return None
            conn.execute("UPDATE holds SET consumed = 1 WHERE reference = ?", (reference,))
            conn.commit()
            return dict(row)

    def set_airtable_id(self, booking_reference: str, airtable_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE bookings SET airtable_record_id = ?, updated_at = ? WHERE booking_reference = ?",
                (airtable_id, _now_iso(), booking_reference),
            )
            conn.commit()


class ViatorSupplierService:
    def __init__(self, agent=None, config_override: Optional[dict] = None, db_path: Optional[str] = None):
        self.agent = agent
        self.config = load_viator_config(config_override)
        self.catalog = ProductCatalog(self.config.get("products_file") or "viator_products.json")
        self.store = ViatorStore(db_path=db_path)

    def health(self) -> dict:
        live = self.catalog.live_products()
        return {
            "status": "ok",
            "service": "viator-supplier",
            "environment": self.config.get("environment") or "sandbox",
            "live_products": len(live),
            "api_connected_products": self.catalog.connected_codes(),
            "supplier_id_configured": bool(self.config.get("supplier_id")),
            "api_key_configured": bool(_accepted_api_keys(self.config)),
            "timestamp": _now_iso(),
        }

    def remaining_capacity(self, product: dict, travel_day: date, option: Optional[dict] = None) -> int:
        daily = max(0, _as_int(product.get("daily_capacity"), 0))
        code = product.get("supplier_product_code")
        date_str = travel_day.isoformat()
        option_code = (option or {}).get("supplier_option_code") or ""
        departure = (option or {}).get("departure_time") or ""
        booked = self.store.booked_pax(code, date_str, option_code, departure)
        held = self.store.held_pax(code, date_str, option_code, departure)
        return max(0, daily - booked - held)

    def _is_closed(self, product: dict, travel_day: date, option: Optional[dict] = None) -> tuple[bool, str]:
        if travel_day.weekday() in set(product.get("closed_weekdays") or []):
            return True, "CLOSED"
        if travel_day.isoformat() in set(product.get("blockout_dates") or []):
            return True, "BLOCKED_OUT"
        cutoff_hours = _as_int(product.get("cutoff_hours"), 0)
        if cutoff_hours:
            dep = _hhmm((option or {}).get("departure_time") or "00:00")
            hour, minute = [int(p) for p in dep.split(":")]
            start_local = datetime.combine(travel_day, datetime.min.time()).replace(
                hour=hour, minute=minute, tzinfo=timezone(timedelta(hours=2))
            )
            if _now_utc() > start_local.astimezone(timezone.utc) - timedelta(hours=cutoff_hours):
                return True, "PAST_CUTOFF"
        return False, ""

    def _price_items(self, option: dict) -> list[dict]:
        items = []
        mapping = [
            ("Adult", "adult_retail", "adult_net"),
            ("Child", "child_retail", "child_net"),
            ("Youth", "youth_retail", "youth_net"),
            ("Infant", "infant_retail", "infant_net"),
            ("Senior", "senior_retail", "senior_net"),
        ]
        for band, retail_key, net_key in mapping:
            retail = option.get(retail_key)
            if retail is None and band in ("Youth", "Senior"):
                continue
            if retail is None:
                retail = 0
            items.append({
                "AgeBand": band,
                "RetailPrice": _as_float(retail),
                "NetPrice": _as_float(option.get(net_key, retail)),
            })
        return items

    def _v2_price(self, option: dict) -> dict:
        prices = []
        for band, retail_key, net_key in (
            ("ADULT", "adult_retail", "adult_net"),
            ("CHILD", "child_retail", "child_net"),
            ("YOUTH", "youth_retail", "youth_net"),
            ("INFANT", "infant_retail", "infant_net"),
            ("SENIOR", "senior_retail", "senior_net"),
        ):
            if option.get(retail_key) is None and band not in ("ADULT", "CHILD", "INFANT"):
                continue
            prices.append({
                "types": [band],
                "retailPrice": _as_float(option.get(retail_key), 0),
                "netPrice": _as_float(option.get(net_key, option.get(retail_key)), 0),
            })
        return {"type": "PER_PERSON_PRICE", "prices": prices}

    def _cutoff_iso(self, product: dict, travel_day: date, option: dict) -> str:
        cutoff_hours = _as_int(product.get("cutoff_hours"), 0)
        dep = _hhmm(option.get("departure_time") or "00:00")
        hour, minute = [int(p) for p in dep.split(":")]
        start_local = datetime.combine(travel_day, datetime.min.time()).replace(
            hour=hour, minute=minute, tzinfo=timezone(timedelta(hours=2))
        )
        return (start_local - timedelta(hours=cutoff_hours)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def extract_api_key(self, body: Optional[dict] = None) -> str:
        header_key = (
            request.headers.get("X-Api-Key")
            or request.headers.get("Api-Key")
            or request.headers.get("API-Key")
            or ""
        ).strip()
        if header_key:
            return header_key
        data = (body or {}).get("data") if isinstance(body, dict) else None
        if isinstance(data, dict):
            return str(data.get("ApiKey") or "").strip()
        return ""

    def authenticate(self, body: Optional[dict] = None, require_supplier: bool = True) -> Optional[tuple[int, dict]]:
        if not self.config.get("enabled", True):
            return 503, {"error": "SERVICE_UNAVAILABLE", "message": "Viator Supplier API is disabled"}

        allowlist = self.config.get("ip_allowlist") or []
        if allowlist:
            ip = _client_ip()
            if ip not in allowlist:
                LOGGER.warning("Viator request rejected from IP %s", ip)
                return 403, {"error": "FORBIDDEN", "message": "IP not allowed"}

        keys = _accepted_api_keys(self.config)
        if not keys:
            LOGGER.error("Viator Supplier API key is not configured")
            return 401, {"error": "UNAUTHORIZED", "message": "API key is not configured"}

        provided = self.extract_api_key(body)
        if provided not in keys:
            return 401, {"error": "UNAUTHORIZED", "message": "Invalid or missing API key"}

        data = (body or {}).get("data") if isinstance(body, dict) and "data" in body else (body or {})
        expected_supplier = _as_int(self.config.get("supplier_id"), 0)
        incoming_supplier = data.get("SupplierId", data.get("supplierId"))
        if require_supplier and expected_supplier and incoming_supplier is not None:
            if _as_int(incoming_supplier, -1) != expected_supplier:
                return 401, {"error": "INVALID_SUPPLIER", "message": "Invalid supplier ID"}

        expected_reseller = str(self.config.get("reseller_id") or "").strip()
        incoming_reseller = str(data.get("ResellerId") or "").strip()
        if expected_reseller and incoming_reseller and incoming_reseller != expected_reseller:
            return 401, {"error": "INVALID_RESELLER", "message": "Invalid reseller ID"}
        return None

    def v1_envelope(self, response_type: str, data: dict, request_data: Optional[dict] = None,
                    status: str = "SUCCESS", error_code: str = "", error_message: str = "") -> dict:
        req = request_data or {}
        payload = {
            "ApiKey": req.get("ApiKey") or self.extract_api_key({"data": req}),
            "ResellerId": req.get("ResellerId") or self.config.get("reseller_id") or "",
            "SupplierId": req.get("SupplierId") if req.get("SupplierId") is not None else self.config.get("supplier_id"),
            "ExternalReference": req.get("ExternalReference") or "",
            "Timestamp": _now_iso(),
        }
        if status == "SUCCESS":
            payload["RequestStatus"] = {"Status": "SUCCESS"}
        else:
            payload["RequestStatus"] = {
                "Status": "ERROR",
                "Error": {
                    "ErrorCode": error_code or ERR_INTERNAL,
                    "ErrorText": error_message or "Request failed",
                },
            }
            if error_code not in (ERR_AUTH, ERR_INVALID_SUPPLIER, ERR_INVALID_RESELLER):
                LOGGER.error("VIATOR_SCHEMA_FAIL %s %s %s", response_type, error_code, error_message)
        payload.update(data)
        return {"responseType": response_type, "data": payload}

    def handle_tour_list(self, req: dict) -> tuple[int, dict]:
        tours = []
        for product in self.catalog.live_products():
            tour_options = []
            for option in product.get("options") or []:
                tour_options.append({
                    "SupplierOptionCode": option.get("supplier_option_code") or "",
                    "SupplierOptionName": option.get("supplier_option_name") or "",
                    "TourDepartureTime": _hhmmss(option.get("departure_time")),
                    "productOptionId": option.get("product_option_id") or "",
                    "Option": [],
                })
            tours.append({
                "SupplierProductCode": product.get("supplier_product_code"),
                "SupplierProductName": product.get("supplier_product_name"),
                "CountryCode": product.get("country_code") or "EG",
                "DestinationCode": product.get("destination_code") or "",
                "DestinationName": product.get("destination_name") or "",
                "TourDescription": product.get("tour_description") or "",
                "TourOption": tour_options,
            })
        return 200, self.v1_envelope("TourListResponse", {"Tour": tours}, req)

    def _availability_for_day(self, product: dict, option: dict, travel_day: date, requested_pax: int) -> dict:
        closed, reason = self._is_closed(product, travel_day, option)
        remaining = 0 if closed else self.remaining_capacity(product, travel_day, option)
        if closed:
            status = "UNAVAILABLE"
            unavail = reason
            mix_ok = {band: False for band in AGE_BANDS}
        elif remaining <= 0:
            status = "UNAVAILABLE"
            unavail = "SOLD_OUT"
            mix_ok = {band: False for band in AGE_BANDS}
        elif requested_pax and remaining < requested_pax:
            status = "UNAVAILABLE"
            unavail = "TRAVELLER_MISMATCH"
            mix_ok = {band: remaining > 0 for band in AGE_BANDS}
            mix_ok["Infant"] = True
        else:
            status = "AVAILABLE"
            unavail = ""
            mix_ok = {band: True for band in AGE_BANDS}

        availability_status: dict[str, Any] = {
            "Status": status,
            "TravellerMixAvailability": mix_ok,
        }
        if unavail:
            availability_status["UnavailabilityReason"] = unavail

        body = {
            "Date": travel_day.isoformat(),
            "SupplierProductCode": product.get("supplier_product_code"),
            "TourOptions": {
                "SupplierOptionCode": option.get("supplier_option_code") or "",
                "SupplierOptionName": option.get("supplier_option_name") or "",
                "TourDepartureTime": _hhmmss(option.get("departure_time")),
            },
            "AvailabilityStatus": availability_status,
            "BookingCutoff": {"ProductDateTime": self._cutoff_iso(product, travel_day, option).replace("Z", "")},
            "Price": {
                "CurrencyCode": self.catalog.currency,
                "Item": [{"RetailPrice": item["RetailPrice"], "AgeBand": item["AgeBand"]} for item in self._price_items(option)],
            },
            "Capacity": {
                "Simple": {
                    "Remaining": remaining,
                    "ConsumedBy": list(CAPACITY_CONSUMERS),
                }
            },
            "VersionTag": {"Textual": _now_iso()},
        }
        return body

    def handle_availability(self, req: dict) -> tuple[int, dict]:
        product_code = str(req.get("SupplierProductCode") or "").strip()
        product = self.catalog.get_product(product_code)
        if not product or not product.get("live"):
            return 200, self.v1_envelope(
                "AvailabilityResponse", {}, req, status="ERROR",
                error_code=ERR_INVALID_PRODUCT, error_message="Invalid product",
            )
        start = _parse_date(req.get("StartDate") or req.get("TravelDate"))
        end = _parse_date(req.get("EndDate")) or start
        if not start:
            return 200, self.v1_envelope(
                "AvailabilityResponse", {}, req, status="ERROR",
                error_code=ERR_VALIDATION, error_message="StartDate is required",
            )
        mix = req.get("TravellerMix") or {}
        requested_pax = _as_int(mix.get("Total"), 0)
        if not requested_pax:
            requested_pax = sum(_as_int(mix.get(band), 0) for band in AGE_BANDS)

        tour_options_req = req.get("TourOptions") or {}
        options = product.get("options") or []
        if tour_options_req:
            matched = self.catalog.get_option(
                product,
                option_code=tour_options_req.get("SupplierOptionCode") or "",
                departure=tour_options_req.get("TourDepartureTime") or "",
            )
            options = [matched] if matched else []
            if not options:
                return 200, self.v1_envelope(
                    "AvailabilityResponse", {}, req, status="ERROR",
                    error_code=ERR_INVALID_OPTION, error_message="Invalid product option",
                )

        rows = []
        hold_info = None
        for day in _date_range(start, end):
            for option in options:
                row = self._availability_for_day(product, option, day, requested_pax)
                if req.get("AvailabilityHold") and row["AvailabilityStatus"]["Status"] == "AVAILABLE" and start == end:
                    hold_info = self.store.create_hold(
                        product.get("supplier_product_code"),
                        option.get("supplier_option_code") or "",
                        option.get("product_option_id") or "",
                        day.isoformat(),
                        option.get("departure_time") or "",
                        requested_pax or 1,
                        mix,
                    )
                    row["AvailabilityHold"] = {
                        "Expiry": f"PT{HOLD_SECONDS}S",
                        "Reference": hold_info["reference"],
                    }
                rows.append(row)

        return 200, self.v1_envelope(
            "AvailabilityResponse",
            {"SupplierProductCode": product.get("supplier_product_code"), "TourAvailability": rows},
            req,
        )

    def handle_batch_availability(self, req: dict) -> tuple[int, dict]:
        start = _parse_date(req.get("StartDate"))
        end = _parse_date(req.get("EndDate")) or start
        if not start or not end:
            return 200, self.v1_envelope(
                "BatchAvailabilityResponse", {}, req, status="ERROR",
                error_code=ERR_VALIDATION, error_message="StartDate and EndDate are required",
            )
        products = self.catalog.live_products()
        wanted = req.get("SupplierProductCode")
        if wanted:
            codes = wanted if isinstance(wanted, list) else [wanted]
            products = [p for p in products if p.get("supplier_product_code") in codes]
        rows = []
        for day in _date_range(start, end):
            for product in products:
                for option in product.get("options") or []:
                    row = self._availability_for_day(product, option, day, requested_pax=0)
                    rows.append({
                        "Date": row["Date"],
                        "SupplierProductCode": row["SupplierProductCode"],
                        "TourOptions": row["TourOptions"],
                        "AvailabilityStatus": {
                            k: v for k, v in row["AvailabilityStatus"].items()
                            if k != "TravellerMixAvailability"
                        },
                        "Capacity": row["Capacity"],
                        "VersionTag": row["VersionTag"],
                    })
        return 200, self.v1_envelope("BatchAvailabilityResponse", {"BatchTourAvailability": rows}, req)

    def _travelers_from_payload(self, data: dict) -> tuple[str, str, dict]:
        mix = data.get("TravellerMix") or {}
        counts = {
            "adults": _as_int(mix.get("Adult"), 0),
            "children": _as_int(mix.get("Child"), 0),
            "youth": _as_int(mix.get("Youth"), 0),
            "infants": _as_int(mix.get("Infant"), 0),
            "seniors": _as_int(mix.get("Senior"), 0),
        }
        total = _as_int(mix.get("Total"), 0) or sum(counts.values())
        counts["total_pax"] = total
        travelers = data.get("Traveller") or []
        if isinstance(travelers, dict):
            travelers = [travelers]
        names = []
        lead = ""
        for person in travelers:
            full = f"{person.get('GivenName') or ''} {person.get('Surname') or ''}".strip()
            if full:
                names.append(full)
            if person.get("LeadTraveller") and full:
                lead = full
        if not lead and names:
            lead = names[0]
        return lead, ", ".join(names), counts

    def _questions_text(self, data: dict) -> str:
        required = data.get("RequiredInfo") or {}
        questions = required.get("Question") or []
        if isinstance(questions, dict):
            questions = [questions]
        lines = []
        for item in questions:
            text = str(item.get("QuestionText") or "").strip()
            answer = str(item.get("QuestionAnswer") or "").strip()
            if text or answer:
                lines.append(f"{text}: {answer}".strip(": "))
        return "\n".join(lines)

    def _booking_record_from_request(self, data: dict, status: str) -> tuple[Optional[dict], Optional[str]]:
        ref = _normalize_booking_ref(data.get("BookingReference"))
        if not ref:
            return None, "BookingReference is required"
        product_code = str(data.get("SupplierProductCode") or "").strip()
        product = self.catalog.get_product(product_code)
        if not product:
            return None, "Invalid product"
        tour_options = data.get("TourOptions") or {}
        option = self.catalog.get_option(
            product,
            option_code=tour_options.get("SupplierOptionCode") or "",
            departure=tour_options.get("TourDepartureTime") or "",
        ) or ((product.get("options") or [None])[0])
        lead, names, counts = self._travelers_from_payload(data)
        contact = data.get("ContactDetail") or {}
        email = str(data.get("ContactEmail") or "").strip()
        notes_parts = [str(data.get("SpecialRequirement") or "").strip(), self._questions_text(data)]
        if email and _is_proxy_email(email):
            notes_parts.append(f"Viator relay email: {email}")
        record = {
            "booking_reference": ref,
            "supplier_confirmation": f"FTS-{ref}",
            "status": status,
            "travel_date": str(data.get("TravelDate") or "")[:10],
            "product_code": product.get("supplier_product_code"),
            "option_code": (option or {}).get("supplier_option_code") or tour_options.get("SupplierOptionCode") or "",
            "option_name": (option or {}).get("supplier_option_name") or tour_options.get("SupplierOptionName") or "",
            "departure_time": _hhmmss(tour_options.get("TourDepartureTime") or (option or {}).get("departure_time")),
            "lead_name": lead,
            "traveler_names": names,
            "adults": counts["adults"],
            "children": counts["children"],
            "youth": counts["youth"],
            "infants": counts["infants"],
            "seniors": counts["seniors"],
            "total_pax": counts["total_pax"],
            "pickup_point": str(data.get("PickupPoint") or "").strip(),
            "phone": _clean_phone(contact.get("ContactValue")),
            "email": email if email and not _is_proxy_email(email) else "",
            "notes": "\n".join([p for p in notes_parts if p]),
            "questions_json": json.dumps((data.get("RequiredInfo") or {}), ensure_ascii=False),
            "net_amount": _as_float(data.get("Amount"), 0),
            "currency": str(data.get("CurrencyCode") or self.catalog.currency),
            "location": _map_location(str(data.get("Location") or product.get("location") or "")),
            "payload_json": json.dumps(_redact(data), ensure_ascii=False, default=str),
            "hold_reference": str(data.get("AvailabilityHoldReference") or ""),
            "viator_product_code": product.get("viator_product_code") or "",
            "tour_name": product.get("supplier_product_name") or "",
        }
        return record, None

    def handle_booking(self, req: dict) -> tuple[int, dict]:
        existing = self.store.get_booking(req.get("BookingReference"))
        if existing and existing.get("status") not in ("CANCELLED", "Canceled"):
            return 200, self._booking_response("BookingResponse", req, existing, "CONFIRMED")

        record, error = self._booking_record_from_request(req, "CONFIRMED")
        if error:
            code = ERR_INVALID_PRODUCT if "product" in error.lower() else ERR_VALIDATION
            return 200, self.v1_envelope(
                "BookingResponse", {}, req, status="ERROR", error_code=code, error_message=error,
            )

        product = self.catalog.get_product(record["product_code"])
        travel_day = _parse_date(record["travel_date"])
        option = self.catalog.get_option(product, option_code=record["option_code"], departure=record["departure_time"]) if product else None
        hold_ref = record.get("hold_reference")
        if hold_ref:
            self.store.consume_hold(hold_ref)
        if product and travel_day:
            remaining = self.remaining_capacity(product, travel_day, option)
            consuming = record["adults"] + record["children"] + record["youth"] + record["seniors"]
            if consuming > remaining:
                return 200, self.v1_envelope(
                    "BookingResponse", {}, req, status="ERROR",
                    error_code=ERR_TRAVELLER_MIX, error_message="Not enough remaining capacity",
                )

        saved = self.store.upsert_booking(record)
        self._push_airtable(saved, event="booking")
        return 200, self._booking_response("BookingResponse", req, saved, "CONFIRMED")

    def handle_amendment(self, req: dict) -> tuple[int, dict]:
        existing = self.store.get_booking(req.get("BookingReference"))
        if not existing:
            return 200, self.v1_envelope(
                "BookingAmendmentResponse", {}, req, status="ERROR",
                error_code=ERR_INVALID_DATA, error_message="Booking not found",
            )
        record, error = self._booking_record_from_request(req, "AMENDED")
        if error:
            return 200, self.v1_envelope(
                "BookingAmendmentResponse", {}, req, status="ERROR",
                error_code=ERR_VALIDATION, error_message=error,
            )
        record["supplier_confirmation"] = existing.get("supplier_confirmation") or record["supplier_confirmation"]
        record["airtable_record_id"] = existing.get("airtable_record_id") or ""
        saved = self.store.upsert_booking(record)
        self._push_airtable(saved, event="amend")
        return 200, self._booking_response("BookingAmendmentResponse", req, saved, "CONFIRMED")

    def handle_cancellation(self, req: dict) -> tuple[int, dict]:
        existing = self.store.get_booking(req.get("BookingReference"))
        if not existing:
            return 200, self.v1_envelope(
                "BookingCancellationResponse", {}, req, status="ERROR",
                error_code=ERR_INVALID_DATA, error_message="Booking not found",
            )
        existing["status"] = "CANCELLED"
        existing["notes"] = "\n".join(filter(None, [
            existing.get("notes") or "",
            f"Cancelled: {req.get('Reason') or ''} {req.get('CancelDate') or ''}".strip(),
        ]))
        saved = self.store.upsert_booking(existing)
        self._push_airtable(saved, event="cancel", extra={"cancel_date": str(req.get("CancelDate") or "")[:10]})
        body = {
            "BookingReference": saved["booking_reference"],
            "SupplierConfirmationNumber": saved.get("supplier_confirmation") or "",
            "SupplierCancellationNumber": f"CXL-{saved['booking_reference']}",
            "TransactionStatus": {"Status": "CONFIRMED"},
        }
        return 200, self.v1_envelope("BookingCancellationResponse", body, req)

    def handle_redemption(self, req: dict) -> tuple[int, dict]:
        existing = self.store.get_booking(req.get("BookingReference"))
        redeemed = bool(existing and existing.get("status") not in ("CANCELLED", "Canceled"))
        body = {
            "RedemptionStatus": False if not existing else redeemed,
            "BookingReference": _normalize_booking_ref(req.get("BookingReference")),
        }
        return 200, self.v1_envelope("RedemptionResponse", body, req)

    def _booking_response(self, response_type: str, req: dict, saved: dict, txn_status: str) -> dict:
        travelers = []
        names = [n.strip() for n in (saved.get("traveler_names") or "").split(",") if n.strip()]
        for idx, name in enumerate(names or [saved.get("lead_name") or "Traveller"], start=1):
            travelers.append({
                "TravellerIdentifier": str(idx),
                "TravellerSupplierConfirmationNumber": saved.get("supplier_confirmation") or "",
                "TravellerSeat": "",
                "TravellerBarcode": "",
            })
        body = {
            "BookingReference": saved.get("booking_reference"),
            "SupplierConfirmationNumber": saved.get("supplier_confirmation") or "",
            "TransactionStatus": {"Status": txn_status},
            "Traveller": travelers,
        }
        return self.v1_envelope(response_type, body, req)

    def handle_v2_calendar(self, body: dict) -> tuple[int, dict]:
        start = _parse_date(body.get("startDate"))
        end = _parse_date(body.get("endDate")) or start
        option_ids = body.get("productOptionIds") or []
        if not start or not option_ids:
            return 422, {"error": "INVALID_REQUEST", "message": "startDate and productOptionIds are required"}
        product_options = []
        for option_id in option_ids:
            product, option = self.catalog.option_by_id(option_id)
            if not product or not option or not product.get("live"):
                continue
            dates = []
            for day in _date_range(start, end):
                closed, reason = self._is_closed(product, day, option)
                remaining = 0 if closed else self.remaining_capacity(product, day, option)
                if closed and reason == "PAST_CUTOFF":
                    status = "UNAVAILABLE"
                elif remaining <= 0:
                    status = "SOLD_OUT"
                else:
                    status = "AVAILABLE"
                dates.append({
                    "travelDate": day.isoformat(),
                    "events": [{
                        "status": status,
                        "startTime": _hhmm(option.get("departure_time")),
                        "capacity": {
                            "type": "LIMITED",
                            "vacancies": [{
                                "types": list(CAPACITY_CONSUMERS),
                                "quantity": remaining,
                                "quantityType": "SHARED",
                            }],
                            "original": _as_int(product.get("daily_capacity"), 0),
                            "remaining": remaining,
                        },
                        "bookingCutoff": self._cutoff_iso(product, day, option),
                        "price": self._v2_price(option),
                    }],
                })
            product_options.append({
                "productOptionId": option_id,
                "currency": self.catalog.currency,
                "dates": dates,
            })
        return 200, {"productOptions": product_options}

    def handle_v2_availability_check(self, body: dict) -> tuple[int, dict]:
        travel_day = _parse_date(body.get("travelDate"))
        product_options_req = body.get("productOptions") or []
        tickets = body.get("tickets") or []
        requested = _as_int(body.get("totalTravelers"), 0)
        if not requested:
            requested = sum(_as_int(t.get("quantity"), 0) for t in tickets if str(t.get("type") or "").upper() != "INFANT")
        if not travel_day or not product_options_req:
            return 422, {"error": "INVALID_REQUEST", "message": "travelDate and productOptions are required"}
        out = []
        for item in product_options_req:
            option_id = item.get("productOptionId")
            product, option = self.catalog.option_by_id(option_id)
            if not product or not option or not product.get("live"):
                continue
            start_times = item.get("startTimes") or [_hhmm(option.get("departure_time"))]
            events = []
            for start in start_times:
                option_copy = dict(option)
                option_copy["departure_time"] = _hhmmss(start)
                closed, reason = self._is_closed(product, travel_day, option_copy)
                remaining = 0 if closed else self.remaining_capacity(product, travel_day, option_copy)
                if closed and reason == "PAST_CUTOFF":
                    status = "UNAVAILABLE"
                elif remaining <= 0 or (requested and remaining < requested):
                    status = "SOLD_OUT" if remaining <= 0 else "UNAVAILABLE"
                else:
                    status = "AVAILABLE"
                events.append({
                    "status": status,
                    "startTime": _hhmm(start),
                    "capacity": {
                        "type": "LIMITED",
                        "vacancies": [{
                            "types": list(CAPACITY_CONSUMERS),
                            "quantity": remaining,
                            "quantityType": "SHARED",
                        }],
                        "original": _as_int(product.get("daily_capacity"), 0),
                        "remaining": remaining,
                    },
                    "bookingCutoff": self._cutoff_iso(product, travel_day, option_copy),
                    "price": self._v2_price(option),
                })
            out.append({
                "productOptionId": option_id,
                "currency": self.catalog.currency,
                "events": events,
            })
        return 200, {"productOptions": out}

    def handle_v2_reserve(self, body: dict) -> tuple[int, dict]:
        option_id = str(body.get("productOptionId") or "").strip()
        product, option = self.catalog.option_by_id(option_id)
        if not product or not option:
            return 422, {"error": "INVALID_PRODUCT_OPTION", "message": "Unknown productOptionId"}
        travel_day = _parse_date(body.get("travelDate"))
        if not travel_day:
            return 422, {"error": "INVALID_REQUEST", "message": "travelDate is required"}
        start_time = body.get("startTime") or option.get("departure_time")
        tickets = body.get("tickets") or []
        total = _as_int(body.get("totalTravelers"), 0)
        if not total:
            total = sum(_as_int(t.get("quantity"), 0) for t in tickets if str(t.get("type") or "").upper() != "INFANT")
        option_copy = dict(option)
        option_copy["departure_time"] = _hhmmss(start_time)
        closed, _reason = self._is_closed(product, travel_day, option_copy)
        remaining = 0 if closed else self.remaining_capacity(product, travel_day, option_copy)
        currency = self.catalog.currency
        price = self._v2_price(option)
        if closed or remaining < max(total, 1):
            return 200, {
                "status": "NOT_RESERVED",
                "expiration": (_now_utc() + timedelta(seconds=HOLD_SECONDS)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "reference": "",
                "currency": currency,
                "price": price,
            }
        hold = self.store.create_hold(
            product.get("supplier_product_code"),
            option.get("supplier_option_code") or "",
            option_id,
            travel_day.isoformat(),
            start_time,
            max(total, 1),
            tickets,
        )
        return 200, {
            "status": "RESERVED",
            "expiration": hold["expires_at"],
            "reference": hold["reference"],
            "currency": currency,
            "price": price,
        }

    def dispatch_v1(self, body: dict) -> tuple[int, dict]:
        request_type = str((body or {}).get("requestType") or "").strip()
        data = (body or {}).get("data") or {}
        handlers = {
            "TourListRequest": self.handle_tour_list,
            "AvailabilityRequest": self.handle_availability,
            "BatchAvailabilityRequest": self.handle_batch_availability,
            "BookingRequest": self.handle_booking,
            "BookingAmendmentRequest": self.handle_amendment,
            "BookingCancellationRequest": self.handle_cancellation,
            "RedemptionRequest": self.handle_redemption,
        }
        handler = handlers.get(request_type)
        if not handler:
            return 200, self.v1_envelope(
                "ErrorResponse", {}, data, status="ERROR",
                error_code=ERR_MALFORMED, error_message=f"Unsupported requestType: {request_type}",
            )
        return handler(data)

    def _airtable_fields(self, saved: dict, event: str, extra: Optional[dict] = None) -> dict:
        if FieldIds is None:
            return {}
        extra = extra or {}
        status_map = {
            "booking": "Active",
            "amend": "Changed",
            "cancel": "Canceled",
        }
        product = self.catalog.get_product(saved.get("product_code") or "")
        tour_name = saved.get("tour_name") or (product or {}).get("supplier_product_name") or saved.get("product_code")
        viator_code = saved.get("viator_product_code") or (product or {}).get("viator_product_code") or saved.get("product_code") or ""
        fields = {
            FieldIds.BOOKING_NR: saved.get("booking_reference"),
            FieldIds.AGENCY: "Viator",
            FieldIds.BOOKING_STATUS: status_map.get(event, "Active"),
            FieldIds.DATE_TRIP: saved.get("travel_date"),
            FieldIds.TRIP_NAME: tour_name,
            FieldIds.REAL_PRODUCT_NAME: tour_name or "",
            FieldIds.OPTION: saved.get("option_name") or saved.get("option_code") or "",
            FieldIds.CUSTOMER_NAME: saved.get("lead_name") or "",
            FieldIds.TRAVELER_NAME: saved.get("traveler_names") or "",
            FieldIds.ADT: saved.get("adults") or 0,
            FieldIds.CHD: saved.get("children") or 0,
            FieldIds.INF: saved.get("infants") or 0,
            FieldIds.YOUTH: saved.get("youth") or 0,
            FieldIds.HOTEL_NAME: saved.get("pickup_point") or "",
            FieldIds.DES: saved.get("location") or "",
            FieldIds.AMOUNT: saved.get("net_amount") or 0,
            FieldIds.CURRENCY: saved.get("currency") or "USD",
            FieldIds.NET_RATE: saved.get("net_amount") or 0,
            FieldIds.PRODUCT_ID: viator_code,
            FieldIds.TOTAL_TRAVELERS: saved.get("total_pax") or 0,
            FieldIds.NOTE: saved.get("notes") or "",
        }
        if saved.get("phone"):
            fields[FieldIds.CUSTOMER_PHONE] = saved["phone"]
        if saved.get("email"):
            fields[FieldIds.CUSTOMER_EMAIL] = saved["email"]
        if (saved.get("currency") or "").upper() == "USD" and saved.get("net_amount"):
            fields[FieldIds.TOTAL_PRICE_USD] = saved.get("net_amount")
        remarks = [
            f"Viator API {event}",
            f"Confirmation: {saved.get('supplier_confirmation')}",
            f"Departure: {saved.get('departure_time')}",
            saved.get("notes") or "",
        ]
        fields[FieldIds.REMARKS] = " | ".join([p for p in remarks if p])
        if event == "cancel" and extra.get("cancel_date"):
            fields[FieldIds.CXL_DATE] = extra["cancel_date"]
        return {k: v for k, v in fields.items() if v not in (None, "")}

    def _push_airtable(self, saved: dict, event: str, extra: Optional[dict] = None) -> None:
        if not self.agent:
            return
        payload = deepcopy(saved)
        extra = extra or {}

        def worker():
            try:
                self._upsert_airtable(payload, event, extra)
            except Exception as exc:
                LOGGER.error("Viator Airtable upsert failed for %s: %s", payload.get("booking_reference"), exc)

        if self.config.get("async_airtable", True):
            threading.Thread(target=worker, daemon=True).start()
        else:
            worker()

    def _upsert_airtable(self, saved: dict, event: str, extra: dict) -> None:
        agent = self.agent
        if not agent or not getattr(agent, "table", None):
            return
        ref = saved.get("booking_reference")
        fields = self._airtable_fields(saved, event, extra)
        existing = None
        try:
            existing = agent.find_booking_by_number(ref)
        except Exception as exc:
            LOGGER.warning("Viator booking lookup failed for %s: %s", ref, exc)

        record = None
        if existing:
            record_id = existing.get("id")
            if event == "booking":
                protected = {
                    FieldIds.CUSTOMER_NAME, FieldIds.CUSTOMER_PHONE, FieldIds.CUSTOMER_EMAIL,
                    FieldIds.HOTEL_NAME, FieldIds.TRIP_NAME, FieldIds.REAL_PRODUCT_NAME,
                } if FieldIds else set()
                existing_fields = existing.get("fields") or {}
                to_update = {}
                for key, value in fields.items():
                    if key in protected and existing_fields.get(key):
                        continue
                    to_update[key] = value
                if to_update:
                    record = agent._update_airtable_table_record(agent.table, record_id, to_update, typecast=True)
            else:
                record = agent._update_airtable_table_record(agent.table, record_id, fields, typecast=True)
            airtable_id = record_id
        else:
            record = agent._create_airtable_table_record(agent.table, fields, typecast=True)
            airtable_id = (record or {}).get("id")

        if airtable_id:
            self.store.set_airtable_id(ref, airtable_id)
            try:
                if getattr(agent, "airtable_mirror", None) and record:
                    agent.airtable_mirror.upsert_main_list_record(airtable_id, (record or {}).get("fields") or fields)
            except Exception as exc:
                LOGGER.warning("Viator mirror upsert failed for %s: %s", ref, exc)


def get_service(agent=None, config_override: Optional[dict] = None, db_path: Optional[str] = None) -> ViatorSupplierService:
    global _SERVICE
    if config_override is not None or db_path is not None:
        return ViatorSupplierService(agent=agent, config_override=config_override, db_path=db_path)
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = ViatorSupplierService(agent=agent)
        elif agent is not None and _SERVICE.agent is None:
            _SERVICE.agent = agent
        return _SERVICE


def _json_body() -> dict:
    return request.get_json(silent=True) or {}


def create_viator_blueprint(service: ViatorSupplierService) -> Blueprint:
    bp = Blueprint("viator_supplier", __name__, url_prefix="/viator")

    def _auth_or_error(body: dict, v1: bool = False, request_data: Optional[dict] = None):
        rejected = service.authenticate(body)
        if not rejected:
            return None
        status, payload = rejected
        if v1:
            code = ERR_AUTH if status == 401 else ERR_INVALID_SUPPLIER
            envelope = service.v1_envelope(
                "ErrorResponse", {}, request_data or body.get("data") or {},
                status="ERROR", error_code=code, error_message=payload.get("message") or "Unauthorized",
            )
            return status, envelope
        return status, payload

    def _finish(endpoint: str, request_type: str, status: int, response_body: dict, raw: dict, error: str = ""):
        ref = ""
        data = raw.get("data") if isinstance(raw, dict) else {}
        if isinstance(data, dict):
            ref = str(data.get("BookingReference") or "")
        ref = ref or str((raw or {}).get("BookingReference") or "")
        service.store.log_request(endpoint, request_type, ref, status, raw, response_body, error)
        return jsonify(response_body), status

    @bp.route("/health", methods=["GET"])
    def health():
        return jsonify(service.health()), 200

    @bp.route("", methods=["POST"])
    @bp.route("/", methods=["POST"])
    @bp.route("/v1", methods=["POST"])
    def dispatch():
        body = _json_body()
        auth = _auth_or_error(body, v1=True, request_data=(body or {}).get("data") or {})
        if auth:
            return _finish("dispatch", str(body.get("requestType") or ""), auth[0], auth[1], body)
        status, payload = service.dispatch_v1(body)
        return _finish("dispatch", str(body.get("requestType") or ""), status, payload, body)

    def _v1_endpoint(expected_type: str, handler, endpoint_name: str):
        def view():
            body = _json_body()
            data = body.get("data") if body.get("requestType") else body
            if body.get("requestType") and body.get("requestType") != expected_type:
                fail = service.v1_envelope(
                    expected_type.replace("Request", "Response"), {}, data or {},
                    status="ERROR", error_code=ERR_MALFORMED,
                    error_message=f"Expected {expected_type}",
                )
                return _finish(expected_type, expected_type, 200, fail, body)
            auth = _auth_or_error(body if body.get("data") is not None else {"data": body}, v1=True, request_data=data or {})
            if auth:
                return _finish(expected_type, expected_type, auth[0], auth[1], body)
            status, payload = handler(data or {})
            return _finish(expected_type, expected_type, status, payload, body)
        view.__name__ = endpoint_name
        return view

    v1_routes = [
        ("/tourlist", "TourListRequest", service.handle_tour_list, "viator_tourlist"),
        ("/v1/tour-list", "TourListRequest", service.handle_tour_list, "viator_v1_tour_list"),
        ("/availability", "AvailabilityRequest", service.handle_availability, "viator_availability"),
        ("/v1/availability", "AvailabilityRequest", service.handle_availability, "viator_v1_availability"),
        ("/batch-availability", "BatchAvailabilityRequest", service.handle_batch_availability, "viator_batch_availability"),
        ("/v1/batch-availability", "BatchAvailabilityRequest", service.handle_batch_availability, "viator_v1_batch_availability"),
        ("/booking", "BookingRequest", service.handle_booking, "viator_booking"),
        ("/v1/booking", "BookingRequest", service.handle_booking, "viator_v1_booking"),
        ("/booking-amendment", "BookingAmendmentRequest", service.handle_amendment, "viator_booking_amendment"),
        ("/v1/booking-amendment", "BookingAmendmentRequest", service.handle_amendment, "viator_v1_booking_amendment"),
        ("/booking-cancellation", "BookingCancellationRequest", service.handle_cancellation, "viator_booking_cancellation"),
        ("/v1/booking-cancellation", "BookingCancellationRequest", service.handle_cancellation, "viator_v1_booking_cancellation"),
        ("/redemption", "RedemptionRequest", service.handle_redemption, "viator_redemption"),
    ]
    for path, expected_type, handler, endpoint_name in v1_routes:
        bp.add_url_rule(
            path,
            endpoint=endpoint_name,
            view_func=_v1_endpoint(expected_type, handler, endpoint_name),
            methods=["POST"],
        )

    @bp.route("/v2/availability/calendar", methods=["POST"])
    def v2_calendar():
        body = _json_body()
        auth = _auth_or_error(body)
        if auth:
            return _finish("Calendar", "Calendar", auth[0], auth[1], body)
        status, payload = service.handle_v2_calendar(body)
        return _finish("Calendar", "Calendar", status, payload, body)

    @bp.route("/v2/availability/check", methods=["POST"])
    def v2_check():
        body = _json_body()
        auth = _auth_or_error(body)
        if auth:
            return _finish("AvailabilityCheck", "AvailabilityCheck", auth[0], auth[1], body)
        status, payload = service.handle_v2_availability_check(body)
        return _finish("AvailabilityCheck", "AvailabilityCheck", status, payload, body)

    @bp.route("/v2/reserve", methods=["POST"])
    def v2_reserve():
        body = _json_body()
        auth = _auth_or_error(body)
        if auth:
            return _finish("Reserve", "Reserve", auth[0], auth[1], body)
        status, payload = service.handle_v2_reserve(body)
        return _finish("Reserve", "Reserve", status, payload, body)

    return bp


def register_viator_supplier_routes(app: Flask, agent=None, config_override: Optional[dict] = None, db_path: Optional[str] = None):
    service = get_service(agent=agent, config_override=config_override, db_path=db_path)
    app.register_blueprint(create_viator_blueprint(service))
    LOGGER.info("Viator Supplier API registered under /viator")
    return service


def create_test_app(config_override: Optional[dict] = None, db_path: Optional[str] = None) -> Flask:
    app = Flask(__name__)
    register_viator_supplier_routes(
        app,
        agent=None,
        config_override=config_override,
        db_path=db_path,
    )
    return app
