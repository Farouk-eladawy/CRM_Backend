"""
GetYourGuide Supplier-side API (FTS Travels).

GYG calls OUR HTTPS endpoints. All public routes live under /gyg/1/...

Official contract: https://integrator.getyourguide.com/documentation/supplier_endpoints
"""

from __future__ import annotations

import base64
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
HOLD_SECONDS = 60 * 60  # GYG requires at least 1 hour hold
MAX_CALENDAR_DAYS = 365
CAIRO_TZ = timezone(timedelta(hours=2))
GYG_CATEGORIES = ("ADULT", "CHILD", "INFANT", "SENIOR")
CAPACITY_CATEGORIES = ("ADULT", "CHILD", "SENIOR")
PROXY_EMAIL_MARKERS = ("reply.getyourguide.com",)

ERR_AUTH = "AUTHENTICATION_FAILED"
ERR_INVALID_PRODUCT = "INVALID_PRODUCT"
ERR_NO_AVAILABILITY = "NO_AVAILABILITY"
ERR_VALIDATION = "VALIDATION_ERROR"
ERR_INTERNAL = "INTERNAL_ERROR"
ERR_BOOKING_NOT_FOUND = "BOOKING_NOT_FOUND"
ERR_ALREADY_CANCELLED = "BOOKING_ALREADY_CANCELLED"
ERR_IN_PAST = "BOOKING_IN_PAST"
ERR_REDEEMED = "BOOKING_REDEEMED"

_SERVICE_LOCK = threading.Lock()
_SERVICE: Optional["GYGSupplierService"] = None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    # Query strings often decode '+' in timezone offsets as a space.
    if " " in text and "+" not in text:
        text = text.replace(" ", "+", 1)
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
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
        return f"{int(parts[0]):02d}:{int(parts[1]) if len(parts) > 1 else 0:02d}"
    except (TypeError, ValueError):
        return "00:00"


def _hhmmss(value: Any) -> str:
    return f"{_hhmm(value)}:00"


def _slot_datetime(travel_day: date, departure: str) -> str:
    hh, mm = _hhmm(departure).split(":")
    dt = datetime.combine(travel_day, datetime.min.time()).replace(
        hour=int(hh), minute=int(mm), tzinfo=CAIRO_TZ
    )
    return dt.isoformat(timespec="seconds")


def _slot_key(travel_day: date, departure: str) -> str:
    return f"{travel_day.isoformat()}T{_hhmm(departure)}"


def _redact(payload: Any) -> Any:
    if isinstance(payload, dict):
        out = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in {"password", "authorization", "auth"}:
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


def _normalize_gyg_ref(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    if raw.startswith("GYG"):
        return raw
    return f"GYG{raw}"


def _client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or (request.remote_addr or "").strip()


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
    if "hurghada" in text or "makadi" in text or "el gouna" in text:
        return "Hurghada"
    if "luxor" in text:
        return "Luxor"
    if "cairo" in text or "giza" in text:
        return "Cairo"
    if "marsa alam" in text:
        return "Marsa Alam"
    return (raw or "").split(",")[0].strip() or raw


def _items_to_counts(items: list[dict]) -> tuple[dict[str, int], int]:
    counts = {cat: 0 for cat in GYG_CATEGORIES}
    consuming = 0
    for item in items or []:
        cat = str(item.get("category") or "").upper()
        cnt = _as_int(item.get("count"), 0)
        if cat in counts:
            counts[cat] = cnt
        if cat in CAPACITY_CATEGORIES:
            consuming += cnt
    return counts, consuming


def load_gyg_config(override: Optional[dict] = None) -> dict:
    cfg: dict[str, Any] = {
        "enabled": True,
        "basic_user": "",
        "basic_pass": "",
        "basic_user_sandbox": "",
        "basic_pass_sandbox": "",
        "basic_user_production": "",
        "basic_pass_production": "",
        "supplier_id": "S707722",
        "environment": "sandbox",
        "currency": "EUR",
        "ip_allowlist": [],
        "products_file": "gyg_products.json",
        "async_airtable": True,
    }
    try:
        config_path = os.path.join(SCRIPT_DIR, get_data_path("config.json"))
        if os.path.isfile(config_path):
            with open(config_path, "r", encoding="utf-8") as handle:
                file_cfg = json.load(handle).get("gyg_supplier") or {}
            if isinstance(file_cfg, dict):
                cfg.update(file_cfg)
    except Exception as exc:
        LOGGER.warning("Could not load gyg_supplier config.json section: %s", exc)

    env_map = {
        "GYG_SUPPLIER_BASIC_USER": "basic_user",
        "GYG_SUPPLIER_BASIC_PASS": "basic_pass",
        "GYG_SUPPLIER_BASIC_USER_SANDBOX": "basic_user_sandbox",
        "GYG_SUPPLIER_BASIC_PASS_SANDBOX": "basic_pass_sandbox",
        "GYG_SUPPLIER_BASIC_USER_PRODUCTION": "basic_user_production",
        "GYG_SUPPLIER_BASIC_PASS_PRODUCTION": "basic_pass_production",
        "GYG_SUPPLIER_ID": "supplier_id",
        "GYG_SUPPLIER_ENV": "environment",
    }
    for env_name, key in env_map.items():
        val = os.environ.get(env_name)
        if val:
            cfg[key] = val

    if override:
        cfg.update(override)
    cfg["ip_allowlist"] = [str(ip).strip() for ip in (cfg.get("ip_allowlist") or []) if str(ip).strip()]
    return cfg


def _accepted_basic_credentials(cfg: dict) -> set[tuple[str, str]]:
    pairs = {
        (str(cfg.get("basic_user") or "").strip(), str(cfg.get("basic_pass") or "").strip()),
        (str(cfg.get("basic_user_sandbox") or "").strip(), str(cfg.get("basic_pass_sandbox") or "").strip()),
        (str(cfg.get("basic_user_production") or "").strip(), str(cfg.get("basic_pass_production") or "").strip()),
    }
    return {(u, p) for u, p in pairs if u and p}


class ProductCatalog:
    def __init__(self, products_file: str):
        self.products_file = products_file
        self.products: list[dict] = []
        self.currency = "EUR"
        self.supplier_id = "S707722"
        self.supplier_name = "FTS Travels"
        self.reload()

    def reload(self) -> None:
        path = self.products_file
        if not os.path.isabs(path):
            path = get_data_path(path)
        if not os.path.isfile(path):
            LOGGER.error("GYG products file missing: %s", path)
            self.products = []
            return
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        self.currency = str(raw.get("currency") or "EUR")
        self.supplier_id = str(raw.get("supplier_id") or "S707722")
        self.supplier_name = str(raw.get("supplier_name") or "FTS Travels")
        self.products = list(raw.get("products") or [])

    def live_products(self) -> list[dict]:
        return [p for p in self.products if p.get("live")]

    def connected_ids(self) -> list[str]:
        return [p.get("product_id") for p in self.products if p.get("api_connected")]

    def get_product(self, product_id: str) -> Optional[dict]:
        wanted = str(product_id or "").strip()
        if not wanted:
            return None
        for product in self.products:
            if product.get("product_id") == wanted:
                return product
            if str(product.get("gyg_tour_id") or "") == wanted:
                return product
        return None


class GYGStore:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_data_path("gyg_supplier.db")
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
                    gyg_booking_reference TEXT PRIMARY KEY,
                    booking_reference TEXT,
                    status TEXT,
                    travel_date TEXT,
                    travel_datetime TEXT,
                    product_id TEXT,
                    lead_name TEXT,
                    traveler_names TEXT,
                    adults INTEGER DEFAULT 0,
                    children INTEGER DEFAULT 0,
                    infants INTEGER DEFAULT 0,
                    seniors INTEGER DEFAULT 0,
                    total_pax INTEGER DEFAULT 0,
                    pickup_point TEXT,
                    phone TEXT,
                    email TEXT,
                    notes TEXT,
                    retail_amount REAL DEFAULT 0,
                    currency TEXT,
                    location TEXT,
                    payload_json TEXT,
                    airtable_record_id TEXT,
                    reservation_reference TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS holds (
                    reference TEXT PRIMARY KEY,
                    gyg_booking_reference TEXT,
                    product_id TEXT,
                    travel_date TEXT,
                    travel_datetime TEXT,
                    slot_key TEXT,
                    total_pax INTEGER DEFAULT 0,
                    items_json TEXT,
                    expires_at TEXT,
                    consumed INTEGER DEFAULT 0,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS request_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT,
                    gyg_booking_reference TEXT,
                    status_code INTEGER,
                    request_json TEXT,
                    response_json TEXT,
                    error TEXT,
                    created_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_gyg_bookings_capacity
                    ON bookings(travel_date, product_id, status);
                CREATE INDEX IF NOT EXISTS idx_gyg_holds_capacity
                    ON holds(travel_date, product_id, consumed);
                """
            )
            conn.commit()

    def log_request(self, endpoint: str, gyg_ref: str, status_code: int,
                    request_json: Any, response_json: Any, error: str = "") -> None:
        try:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO request_logs
                    (endpoint, gyg_booking_reference, status_code, request_json, response_json, error, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        endpoint,
                        gyg_ref or "",
                        status_code,
                        json.dumps(_redact(request_json), ensure_ascii=False, default=str)[:20000],
                        json.dumps(_redact(response_json), ensure_ascii=False, default=str)[:20000],
                        (error or "")[:2000],
                        _now_iso(),
                    ),
                )
                conn.commit()
        except Exception as exc:
            LOGGER.warning("Failed to log GYG request: %s", exc)

    def get_booking_by_gyg(self, gyg_ref: str) -> Optional[dict]:
        ref = _normalize_gyg_ref(gyg_ref)
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM bookings WHERE gyg_booking_reference = ?",
                (ref,),
            ).fetchone()
        return dict(row) if row else None

    def get_booking_by_our_ref(self, booking_reference: str) -> Optional[dict]:
        ref = str(booking_reference or "").strip()
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM bookings WHERE booking_reference = ?",
                (ref,),
            ).fetchone()
        return dict(row) if row else None

    def upsert_booking(self, record: dict) -> dict:
        ref = record["gyg_booking_reference"]
        now = _now_iso()
        record = dict(record)
        record.setdefault("created_at", now)
        record["updated_at"] = now
        columns = [
            "gyg_booking_reference", "booking_reference", "status", "travel_date", "travel_datetime",
            "product_id", "lead_name", "traveler_names", "adults", "children", "infants", "seniors",
            "total_pax", "pickup_point", "phone", "email", "notes", "retail_amount", "currency",
            "location", "payload_json", "airtable_record_id", "reservation_reference",
            "created_at", "updated_at",
        ]
        placeholders = ", ".join("?" for _ in columns)
        assignments = ", ".join(f"{c}=excluded.{c}" for c in columns if c not in ("gyg_booking_reference", "created_at"))
        values = [record.get(c) for c in columns]
        with self._lock, self._connect() as conn:
            conn.execute(
                f"""
                INSERT INTO bookings ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(gyg_booking_reference) DO UPDATE SET {assignments},
                    created_at=bookings.created_at
                """,
                values,
            )
            conn.commit()
        return self.get_booking_by_gyg(ref) or record

    def booked_pax(self, product_id: str, travel_date: str, slot_key: str = "") -> int:
        sql = """
            SELECT COALESCE(SUM(adults + children + seniors), 0)
            FROM bookings
            WHERE product_id = ?
              AND travel_date = ?
              AND status IN ('CONFIRMED', 'Active', 'Changed')
        """
        params: list[Any] = [product_id, travel_date]
        if slot_key:
            sql += " AND travel_datetime LIKE ?"
            params.append(f"{travel_date}T{slot_key.split('T', 1)[-1]}%")
        with self._lock, self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row[0] if row else 0)

    def held_pax(self, product_id: str, travel_date: str, slot_key: str = "") -> int:
        now = _now_iso()
        sql = """
            SELECT COALESCE(SUM(total_pax), 0)
            FROM holds
            WHERE product_id = ?
              AND travel_date = ?
              AND consumed = 0
              AND expires_at > ?
        """
        params: list[Any] = [product_id, travel_date, now]
        if slot_key:
            sql += " AND slot_key = ?"
            params.append(slot_key)
        with self._lock, self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row[0] if row else 0)

    def create_hold(self, gyg_ref: str, product_id: str, travel_date: str,
                    travel_datetime: str, slot_key: str, total_pax: int, items: Any) -> dict:
        reference = f"RES-{uuid.uuid4().hex[:12].upper()}"
        expires_at = (_now_utc() + timedelta(seconds=HOLD_SECONDS)).isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO holds
                (reference, gyg_booking_reference, product_id, travel_date, travel_datetime,
                 slot_key, total_pax, items_json, expires_at, consumed, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    reference, _normalize_gyg_ref(gyg_ref), product_id, travel_date, travel_datetime,
                    slot_key, total_pax, json.dumps(items or []), expires_at, _now_iso(),
                ),
            )
            conn.commit()
        return {"reservationReference": reference, "reservationExpiration": expires_at}

    def get_hold(self, reference: str) -> Optional[dict]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT * FROM holds WHERE reference = ?", (reference,)).fetchone()
        return dict(row) if row else None

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

    def release_hold(self, reference: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("UPDATE holds SET consumed = 1 WHERE reference = ?", (reference,))
            conn.commit()

    def set_airtable_id(self, gyg_ref: str, airtable_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE bookings SET airtable_record_id = ?, updated_at = ? WHERE gyg_booking_reference = ?",
                (airtable_id, _now_iso(), _normalize_gyg_ref(gyg_ref)),
            )
            conn.commit()


class GYGSupplierService:
    def __init__(self, agent=None, config_override: Optional[dict] = None, db_path: Optional[str] = None):
        self.agent = agent
        self.config = load_gyg_config(config_override)
        self.catalog = ProductCatalog(self.config.get("products_file") or "gyg_products.json")
        self.store = GYGStore(db_path=db_path)

    def health(self) -> dict:
        live = self.catalog.live_products()
        return {
            "status": "ok",
            "service": "gyg-supplier",
            "environment": self.config.get("environment") or "sandbox",
            "live_products": len(live),
            "api_connected_products": self.catalog.connected_ids(),
            "supplier_id_configured": bool(self.config.get("supplier_id")),
            "basic_auth_configured": bool(_accepted_basic_credentials(self.config)),
            "timestamp": _now_iso(),
        }

    def _success(self, payload: dict) -> dict:
        return {"data": payload}

    def _error(self, code: str, message: str) -> dict:
        LOGGER.error("GYG_SCHEMA_FAIL %s %s", code, message)
        return {"data": {"errorCode": code, "errorMessage": message}}

    def _extract_basic_auth(self) -> tuple[str, str]:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("basic "):
            try:
                decoded = base64.b64decode(auth.split(" ", 1)[1].strip()).decode("utf-8")
                user, _, password = decoded.partition(":")
                return user.strip(), password.strip()
            except Exception:
                return "", ""
        return "", ""

    def authenticate(self) -> Optional[tuple[int, dict]]:
        if not self.config.get("enabled", True):
            return 503, self._error("SERVICE_UNAVAILABLE", "GYG Supplier API is disabled")

        allowlist = self.config.get("ip_allowlist") or []
        if allowlist:
            ip = _client_ip()
            if ip not in allowlist:
                LOGGER.warning("GYG request rejected from IP %s", ip)
                return 403, self._error("FORBIDDEN", "IP not allowed")

        creds = _accepted_basic_credentials(self.config)
        if not creds:
            LOGGER.error("GYG Supplier Basic Auth is not configured")
            return 401, self._error(ERR_AUTH, "Credentials are not configured")

        user, password = self._extract_basic_auth()
        if (user, password) not in creds:
            return 401, self._error(ERR_AUTH, "Invalid or missing Basic Auth credentials")
        return None

    def remaining_capacity(self, product: dict, travel_day: date, departure: str) -> int:
        daily = max(0, _as_int(product.get("daily_capacity"), 0))
        product_id = product.get("product_id")
        date_str = travel_day.isoformat()
        slot = _slot_key(travel_day, departure)
        booked = self.store.booked_pax(product_id, date_str, slot)
        held = self.store.held_pax(product_id, date_str, slot)
        return max(0, daily - booked - held)

    def _is_closed(self, product: dict, travel_day: date, departure: str) -> bool:
        if travel_day.weekday() in set(product.get("closed_weekdays") or []):
            return True
        if travel_day.isoformat() in set(product.get("blockout_dates") or []):
            return True
        cutoff_hours = _as_int(product.get("cutoff_hours"), 0)
        if cutoff_hours:
            hh, mm = _hhmm(departure).split(":")
            start_local = datetime.combine(travel_day, datetime.min.time()).replace(
                hour=int(hh), minute=int(mm), tzinfo=CAIRO_TZ
            )
            if _now_utc() > start_local.astimezone(timezone.utc) - timedelta(hours=cutoff_hours):
                return True
        return False

    def _prices_by_category(self, product: dict) -> dict:
        retail_prices = []
        categories = product.get("categories") or {}
        for cat in GYG_CATEGORIES:
            cfg = categories.get(cat) or {}
            if cfg.get("enabled") is False:
                continue
            retail_prices.append({
                "category": cat,
                "price": _as_int(cfg.get("retail_minor"), 0),
            })
        return {
            "currency": self.catalog.currency,
            "pricesByCategory": {"retailPrices": retail_prices},
        }

    def _availability_slot(self, product: dict, travel_day: date, departure: str) -> dict:
        closed = self._is_closed(product, travel_day, departure)
        remaining = 0 if closed else self.remaining_capacity(product, travel_day, departure)
        cutoff_seconds = _as_int(product.get("cutoff_seconds"), _as_int(product.get("cutoff_hours"), 0) * 3600)
        slot = {
            "dateTime": _slot_datetime(travel_day, departure),
            "productId": product.get("product_id"),
            "vacancies": remaining,
        }
        if cutoff_seconds > 0:
            slot["cutoffSeconds"] = cutoff_seconds
        slot.update(self._prices_by_category(product))
        return slot

    def handle_get_availabilities(self, product_id: str, from_dt: str, to_dt: str) -> tuple[int, dict]:
        product = self.catalog.get_product(product_id)
        if not product or not product.get("live"):
            return 200, self._error(ERR_INVALID_PRODUCT, f"Unknown productId: {product_id}")

        start = _parse_iso_datetime(from_dt)
        end = _parse_iso_datetime(to_dt)
        if not start or not end:
            return 400, self._error(ERR_VALIDATION, "fromDateTime and toDateTime are required")

        start_day = start.date()
        end_day = end.date()
        availabilities = []
        for day in _date_range(start_day, end_day):
            for departure in product.get("departure_times") or ["00:00:00"]:
                availabilities.append(self._availability_slot(product, day, departure))
        return 200, self._success({"availabilities": availabilities})

    def handle_reserve(self, data: dict) -> tuple[int, dict]:
        product_id = str(data.get("productId") or "").strip()
        product = self.catalog.get_product(product_id)
        if not product or not product.get("live"):
            return 200, self._error(ERR_INVALID_PRODUCT, f"Unknown productId: {product_id}")

        dt = _parse_iso_datetime(data.get("dateTime"))
        if not dt:
            return 400, self._error(ERR_VALIDATION, "dateTime is required")

        items = data.get("bookingItems") or []
        counts, consuming = _items_to_counts(items)
        if consuming <= 0:
            return 400, self._error(ERR_VALIDATION, "bookingItems must include at least one ticket")

        departure = _hhmmss(dt.strftime("%H:%M:%S"))
        travel_day = dt.date()
        if self._is_closed(product, travel_day, departure):
            return 200, self._error(ERR_NO_AVAILABILITY, "Requested timeslot is not available")

        remaining = self.remaining_capacity(product, travel_day, departure)
        if consuming > remaining:
            return 200, self._error(ERR_NO_AVAILABILITY, "Requested timeslot is not available")

        gyg_ref = _normalize_gyg_ref(data.get("gygBookingReference"))
        hold = self.store.create_hold(
            gyg_ref,
            product.get("product_id"),
            travel_day.isoformat(),
            dt.isoformat(timespec="seconds"),
            _slot_key(travel_day, departure),
            consuming,
            items,
        )
        return 200, self._success(hold)

    def handle_cancel_reservation(self, data: dict) -> tuple[int, dict]:
        ref = str(data.get("reservationReference") or "").strip()
        if not ref:
            return 400, self._error(ERR_VALIDATION, "reservationReference is required")
        self.store.release_hold(ref)
        return 200, self._success({})

    def _booking_record_from_request(self, data: dict, status: str) -> tuple[Optional[dict], Optional[str]]:
        gyg_ref = _normalize_gyg_ref(data.get("gygBookingReference"))
        if not gyg_ref:
            return None, "gygBookingReference is required"

        product_id = str(data.get("productId") or "").strip()
        product = self.catalog.get_product(product_id)
        if not product:
            return None, "Invalid product"

        dt = _parse_iso_datetime(data.get("dateTime"))
        if not dt:
            return None, "dateTime is required"

        items = data.get("bookingItems") or []
        counts, consuming = _items_to_counts(items)
        travelers = data.get("travelers") or []
        if isinstance(travelers, dict):
            travelers = [travelers]
        names = []
        lead = ""
        phone = ""
        email = ""
        for person in travelers:
            full = f"{person.get('firstName') or ''} {person.get('lastName') or ''}".strip()
            if full:
                names.append(full)
            if not lead and full:
                lead = full
            if person.get("phoneNumber"):
                phone = _clean_phone(person.get("phoneNumber"))
            if person.get("email"):
                email = str(person.get("email") or "").strip()

        comment = str(data.get("comment") or "").strip()
        notes_parts = []
        if comment:
            notes_parts.append(comment)
        if email and _is_proxy_email(email):
            notes_parts.append(f"GYG relay email: {email}")

        retail_total = 0.0
        currency = str(data.get("currency") or self.catalog.currency)
        for item in items:
            retail_total += (_as_int(item.get("retailPrice"), 0) / 100.0) * _as_int(item.get("count"), 0)

        record = {
            "gyg_booking_reference": gyg_ref,
            "booking_reference": f"FTS-{gyg_ref}",
            "status": status,
            "travel_date": dt.date().isoformat(),
            "travel_datetime": dt.isoformat(timespec="seconds"),
            "product_id": product.get("product_id"),
            "lead_name": lead,
            "traveler_names": ", ".join(names),
            "adults": counts.get("ADULT", 0),
            "children": counts.get("CHILD", 0),
            "infants": counts.get("INFANT", 0),
            "seniors": counts.get("SENIOR", 0),
            "total_pax": consuming or sum(counts.values()),
            "pickup_point": comment,
            "phone": phone,
            "email": email if email and not _is_proxy_email(email) else "",
            "notes": "\n".join(notes_parts),
            "retail_amount": retail_total,
            "currency": currency,
            "location": _map_location(product.get("location") or product.get("destination_name") or ""),
            "payload_json": json.dumps(_redact(data), ensure_ascii=False, default=str),
            "reservation_reference": str(data.get("reservationReference") or ""),
            "product_title": product.get("product_title") or "",
            "gyg_tour_id": product.get("gyg_tour_id") or "",
        }
        return record, None

    def handle_book(self, data: dict) -> tuple[int, dict]:
        gyg_ref = _normalize_gyg_ref(data.get("gygBookingReference"))
        existing = self.store.get_booking_by_gyg(gyg_ref)
        if existing and existing.get("status") not in ("CANCELLED", "Canceled"):
            return 200, self._success({
                "bookingReference": existing.get("booking_reference"),
                "tickets": self._ticket_payload(existing),
            })

        record, error = self._booking_record_from_request(data, "CONFIRMED")
        if error:
            code = ERR_INVALID_PRODUCT if "product" in error.lower() else ERR_VALIDATION
            return 200, self._error(code, error)

        product = self.catalog.get_product(record["product_id"])
        dt = _parse_iso_datetime(data.get("dateTime"))
        departure = _hhmmss(dt.strftime("%H:%M:%S")) if dt else "00:00:00"
        travel_day = dt.date() if dt else _parse_date(record["travel_date"])
        hold_ref = str(data.get("reservationReference") or "").strip()
        if hold_ref:
            self.store.consume_hold(hold_ref)

        if product and travel_day:
            remaining = self.remaining_capacity(product, travel_day, departure)
            consuming = record["adults"] + record["children"] + record["seniors"]
            if consuming > remaining:
                return 200, self._error(ERR_NO_AVAILABILITY, "Requested timeslot is not available")

        saved = self.store.upsert_booking(record)
        self._push_airtable(saved, event="booking")
        return 200, self._success({
            "bookingReference": saved.get("booking_reference"),
            "tickets": self._ticket_payload(saved),
        })

    def _ticket_payload(self, saved: dict) -> list[dict]:
        tickets = []
        idx = 1
        for cat, field in (("ADULT", "adults"), ("CHILD", "children"), ("INFANT", "infants"), ("SENIOR", "seniors")):
            for _ in range(_as_int(saved.get(field), 0)):
                tickets.append({
                    "category": cat,
                    "ticketCode": f"{saved.get('booking_reference')}-{cat}-{idx}",
                    "ticketCodeType": "QR_CODE",
                })
                idx += 1
        return tickets

    def handle_cancel_booking(self, data: dict) -> tuple[int, dict]:
        gyg_ref = _normalize_gyg_ref(data.get("gygBookingReference"))
        our_ref = str(data.get("bookingReference") or "").strip()
        existing = self.store.get_booking_by_gyg(gyg_ref) or (
            self.store.get_booking_by_our_ref(our_ref) if our_ref else None
        )
        if not existing:
            return 200, self._error(ERR_BOOKING_NOT_FOUND, "Booking not found")
        if existing.get("status") in ("CANCELLED", "Canceled"):
            return 200, self._error(ERR_ALREADY_CANCELLED, "Booking has already been cancelled")

        travel_day = _parse_date(existing.get("travel_date"))
        if travel_day and travel_day < date.today():
            return 200, self._error(ERR_IN_PAST, "Booking is in the past and cannot be canceled")

        existing["status"] = "CANCELLED"
        existing["notes"] = "\n".join(filter(None, [existing.get("notes") or "", "Cancelled via GYG API"]))
        saved = self.store.upsert_booking(existing)
        self._push_airtable(saved, event="cancel")
        return 200, self._success({})

    def handle_products_list(self, supplier_id: str) -> tuple[int, dict]:
        expected = str(self.config.get("supplier_id") or self.catalog.supplier_id)
        if supplier_id and expected and supplier_id != expected:
            return 404, self._error(ERR_INVALID_PRODUCT, "Unknown supplierId")
        products = [
            {
                "productId": p.get("product_id"),
                "productTitle": p.get("product_title") or p.get("product_id"),
            }
            for p in self.catalog.live_products()
        ]
        return 200, self._success({
            "supplierId": expected,
            "supplierName": self.catalog.supplier_name,
            "products": products,
        })

    def handle_product_details(self, product_id: str) -> tuple[int, dict]:
        product = self.catalog.get_product(product_id)
        if not product or not product.get("live"):
            return 404, self._error(ERR_INVALID_PRODUCT, f"Unknown productId: {product_id}")
        return 200, self._success({
            "supplierId": self.catalog.supplier_id,
            "productTitle": product.get("product_title") or product_id,
            "productDescription": product.get("product_description") or "",
            "destinationLocation": {
                "city": product.get("city") or product.get("destination_name") or "",
                "country": product.get("country") or "EGY",
            },
            "configuration": {
                "participantsConfiguration": {
                    "min": _as_int(product.get("participants_min"), 1),
                    "max": _as_int(product.get("participants_max"), _as_int(product.get("daily_capacity"), 15)),
                }
            },
        })

    def handle_pricing_categories(self, product_id: str) -> tuple[int, dict]:
        product = self.catalog.get_product(product_id)
        if not product or not product.get("live"):
            return 404, self._error(ERR_INVALID_PRODUCT, f"Unknown productId: {product_id}")
        pricing_categories = []
        for cat in GYG_CATEGORIES:
            cfg = (product.get("categories") or {}).get(cat) or {}
            if cfg.get("enabled") is False:
                continue
            pricing_categories.append({
                "category": cat,
                "minTicketAmount": _as_int(cfg.get("min_ticket_amount"), 0),
                "maxTicketAmount": _as_int(cfg.get("max_ticket_amount"), 999),
                "ageFrom": _as_int(cfg.get("age_from"), 0),
                "ageTo": _as_int(cfg.get("age_to"), 99),
                "bookingCategory": "STANDARD",
                "price": [{
                    "priceType": "RETAIL_PRICE",
                    "price": _as_int(cfg.get("retail_minor"), 0),
                    "currency": self.catalog.currency,
                }],
            })
        return 200, self._success({"pricingCategories": pricing_categories})

    def handle_notify(self, data: dict) -> tuple[int, dict]:
        LOGGER.warning("GYG product notification received: %s", json.dumps(_redact(data), ensure_ascii=False)[:4000])
        return 200, self._success({})

    def handle_addons(self, product_id: str) -> tuple[int, dict]:
        product = self.catalog.get_product(product_id)
        if not product or not product.get("live"):
            return 404, self._error(ERR_INVALID_PRODUCT, f"Unknown productId: {product_id}")
        return 200, self._success({"addons": list(product.get("addons") or [])})

    def _airtable_fields(self, saved: dict, event: str) -> dict:
        if FieldIds is None:
            return {}
        status_map = {"booking": "Active", "cancel": "Canceled"}
        product = self.catalog.get_product(saved.get("product_id") or "")
        tour_name = saved.get("product_title") or (product or {}).get("product_title") or saved.get("product_id")
        fields = {
            FieldIds.BOOKING_NR: saved.get("gyg_booking_reference"),
            FieldIds.AGENCY: "GetYourGuide",
            FieldIds.BOOKING_STATUS: status_map.get(event, "Active"),
            FieldIds.DATE_TRIP: saved.get("travel_date"),
            FieldIds.TRIP_NAME: tour_name,
            FieldIds.REAL_PRODUCT_NAME: tour_name or "",
            FieldIds.CUSTOMER_NAME: saved.get("lead_name") or "",
            FieldIds.TRAVELER_NAME: saved.get("traveler_names") or "",
            FieldIds.ADT: saved.get("adults") or 0,
            FieldIds.CHD: saved.get("children") or 0,
            FieldIds.INF: saved.get("infants") or 0,
            FieldIds.HOTEL_NAME: saved.get("pickup_point") or "",
            FieldIds.DES: saved.get("location") or "",
            FieldIds.AMOUNT: saved.get("retail_amount") or 0,
            FieldIds.CURRENCY: saved.get("currency") or "EUR",
            FieldIds.NET_RATE: saved.get("retail_amount") or 0,
            FieldIds.PRODUCT_ID: saved.get("gyg_tour_id") or saved.get("product_id") or "",
            FieldIds.TOTAL_TRAVELERS: saved.get("total_pax") or 0,
            FieldIds.NOTE: saved.get("notes") or "",
        }
        if saved.get("phone"):
            fields[FieldIds.CUSTOMER_PHONE] = saved["phone"]
        if saved.get("email"):
            fields[FieldIds.CUSTOMER_EMAIL] = saved["email"]
        if (saved.get("currency") or "").upper() == "EUR" and saved.get("retail_amount"):
            fields[FieldIds.TOTAL_PRICE_EUR] = saved.get("retail_amount")
        remarks = [
            f"GYG API {event}",
            f"Confirmation: {saved.get('booking_reference')}",
            saved.get("notes") or "",
        ]
        fields[FieldIds.REMARKS] = " | ".join([p for p in remarks if p])
        return {k: v for k, v in fields.items() if v not in (None, "")}

    def _push_airtable(self, saved: dict, event: str) -> None:
        if not self.agent:
            return
        payload = deepcopy(saved)

        def worker():
            try:
                self._upsert_airtable(payload, event)
            except Exception as exc:
                LOGGER.error("GYG Airtable upsert failed for %s: %s", payload.get("gyg_booking_reference"), exc)

        if self.config.get("async_airtable", True):
            threading.Thread(target=worker, daemon=True).start()
        else:
            worker()

    def _upsert_airtable(self, saved: dict, event: str) -> None:
        agent = self.agent
        if not agent or not getattr(agent, "table", None):
            return
        ref = saved.get("gyg_booking_reference")
        fields = self._airtable_fields(saved, event)
        existing = None
        try:
            existing = agent.find_booking_by_number(ref)
        except Exception as exc:
            LOGGER.warning("GYG booking lookup failed for %s: %s", ref, exc)

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
                LOGGER.warning("GYG mirror upsert failed for %s: %s", ref, exc)


def get_service(agent=None, config_override: Optional[dict] = None, db_path: Optional[str] = None) -> GYGSupplierService:
    global _SERVICE
    if config_override is not None or db_path is not None:
        return GYGSupplierService(agent=agent, config_override=config_override, db_path=db_path)
    with _SERVICE_LOCK:
        if _SERVICE is None:
            _SERVICE = GYGSupplierService(agent=agent)
        elif agent is not None and _SERVICE.agent is None:
            _SERVICE.agent = agent
        return _SERVICE


def _json_body() -> dict:
    return request.get_json(silent=True) or {}


def _basic_auth_header(user: str, password: str) -> dict:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def create_gyg_blueprint(service: GYGSupplierService) -> Blueprint:
    bp = Blueprint("gyg_supplier", __name__, url_prefix="/gyg")

    def _finish(endpoint: str, status: int, body: dict, raw: Any, gyg_ref: str = ""):
        data = raw.get("data") if isinstance(raw, dict) else {}
        ref = gyg_ref or str((data or {}).get("gygBookingReference") or "")
        service.store.log_request(endpoint, ref, status, raw, body)
        return jsonify(body), status

    def _require_auth():
        rejected = service.authenticate()
        if rejected:
            return rejected
        return None

    @bp.route("/health", methods=["GET"])
    def health():
        return jsonify(service.health()), 200

    @bp.route("/1/get-availabilities/", methods=["GET"], strict_slashes=False)
    @bp.route("/1/get-availabilities", methods=["GET"], strict_slashes=False)
    def get_availabilities():
        auth = _require_auth()
        if auth:
            return _finish("get-availabilities", auth[0], auth[1], dict(request.args))
        status, body = service.handle_get_availabilities(
            request.args.get("productId") or "",
            request.args.get("fromDateTime") or "",
            request.args.get("toDateTime") or "",
        )
        return _finish("get-availabilities", status, body, dict(request.args))

    @bp.route("/1/reserve/", methods=["POST"], strict_slashes=False)
    @bp.route("/1/reserve", methods=["POST"], strict_slashes=False)
    def reserve():
        raw = _json_body()
        auth = _require_auth()
        if auth:
            return _finish("reserve", auth[0], auth[1], raw)
        status, body = service.handle_reserve(raw.get("data") or raw)
        return _finish("reserve", status, body, raw)

    @bp.route("/1/cancel-reservation/", methods=["POST"], strict_slashes=False)
    @bp.route("/1/cancel-reservation", methods=["POST"], strict_slashes=False)
    def cancel_reservation():
        raw = _json_body()
        auth = _require_auth()
        if auth:
            return _finish("cancel-reservation", auth[0], auth[1], raw)
        status, body = service.handle_cancel_reservation(raw.get("data") or raw)
        return _finish("cancel-reservation", status, body, raw)

    @bp.route("/1/book/", methods=["POST"], strict_slashes=False)
    @bp.route("/1/book", methods=["POST"], strict_slashes=False)
    def book():
        raw = _json_body()
        auth = _require_auth()
        if auth:
            return _finish("book", auth[0], auth[1], raw)
        status, body = service.handle_book(raw.get("data") or raw)
        return _finish("book", status, body, raw, str((raw.get("data") or raw).get("gygBookingReference") or ""))

    @bp.route("/1/cancel-booking/", methods=["POST"], strict_slashes=False)
    @bp.route("/1/cancel-booking", methods=["POST"], strict_slashes=False)
    def cancel_booking():
        raw = _json_body()
        auth = _require_auth()
        if auth:
            return _finish("cancel-booking", auth[0], auth[1], raw)
        status, body = service.handle_cancel_booking(raw.get("data") or raw)
        return _finish("cancel-booking", status, body, raw)

    @bp.route("/1/suppliers/<supplier_id>/products/", methods=["GET"], strict_slashes=False)
    @bp.route("/1/suppliers/<supplier_id>/products", methods=["GET"], strict_slashes=False)
    def products_list(supplier_id: str):
        auth = _require_auth()
        if auth:
            return _finish("products-list", auth[0], auth[1], {"supplier_id": supplier_id})
        status, body = service.handle_products_list(supplier_id)
        return _finish("products-list", status, body, {"supplier_id": supplier_id})

    @bp.route("/1/products/<product_id>", methods=["GET"], strict_slashes=False)
    @bp.route("/1/products/<product_id>/", methods=["GET"], strict_slashes=False)
    def product_details(product_id: str):
        auth = _require_auth()
        if auth:
            return _finish("product-details", auth[0], auth[1], {"product_id": product_id})
        status, body = service.handle_product_details(product_id)
        return _finish("product-details", status, body, {"product_id": product_id})

    @bp.route("/1/products/<product_id>/pricing-categories/", methods=["GET"], strict_slashes=False)
    @bp.route("/1/products/<product_id>/pricing-categories", methods=["GET"], strict_slashes=False)
    def pricing_categories(product_id: str):
        auth = _require_auth()
        if auth:
            return _finish("pricing-categories", auth[0], auth[1], {"product_id": product_id})
        status, body = service.handle_pricing_categories(product_id)
        return _finish("pricing-categories", status, body, {"product_id": product_id})

    @bp.route("/1/products/<product_id>/addons/", methods=["GET"], strict_slashes=False)
    @bp.route("/1/products/<product_id>/addons", methods=["GET"], strict_slashes=False)
    def addons(product_id: str):
        auth = _require_auth()
        if auth:
            return _finish("addons", auth[0], auth[1], {"product_id": product_id})
        status, body = service.handle_addons(product_id)
        return _finish("addons", status, body, {"product_id": product_id})

    @bp.route("/1/notify/", methods=["POST"], strict_slashes=False)
    @bp.route("/1/notify", methods=["POST"], strict_slashes=False)
    def notify():
        raw = _json_body()
        auth = _require_auth()
        if auth:
            return _finish("notify", auth[0], auth[1], raw)
        status, body = service.handle_notify(raw.get("data") or raw)
        return _finish("notify", status, body, raw)

    return bp


def register_gyg_supplier_routes(app: Flask, agent=None, config_override: Optional[dict] = None, db_path: Optional[str] = None):
    service = get_service(agent=agent, config_override=config_override, db_path=db_path)
    app.register_blueprint(create_gyg_blueprint(service))
    LOGGER.info("GetYourGuide Supplier API registered under /gyg/1")
    return service


def create_test_app(config_override: Optional[dict] = None, db_path: Optional[str] = None) -> Flask:
    app = Flask(__name__)
    register_gyg_supplier_routes(app, agent=None, config_override=config_override, db_path=db_path)
    return app
