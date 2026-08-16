import re
import logging
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

from airtable_fields import FieldIds


REDIRECT_BASE = "https://redirect.ftstravels.com/"
DEFAULT_TEMPLATE_NAME = "gift_bounce"
GYG_ANALYTICS_TABLE = "GYG Analytics"
BONUS_HURGHADA_CITY_TOUR = "1279014"
BONUS_SHARM_SIGNATURE = "1278978"

# Product catalog:
# - location_path: stable GYG city segment (cairo-l92, dahab-l884, ...)
# - display_name / url: fallbacks when GYG Analytics is unavailable
# Live send rebuilds URL as: /{location_path}/{slug(productName)}-t{productId}/
DEFAULT_OFFER_PRODUCTS: Dict[str, Dict[str, str]] = {
    # Hurghada
    "1191624": {
        "tour": "luxor",
        "location_path": "luxor-l109",
        "display_name": "Hurghada: Luxor Valley of the Kings & Tutankhamun Tomb Trip",
        "url": "https://www.getyourguide.com/luxor-l109/hurghada-luxor-valley-of-the-kings-tutankhamun-tomb-trip-t1191624/",
    },
    "1195745": {
        "tour": "cairoPlane",
        "location_path": "cairo-l92",
        "display_name": "Hurghada: Full-Day Trip to Cairo by Plane",
        "url": "https://www.getyourguide.com/cairo-l92/hurghada-full-day-trip-to-cairo-by-plane-t1195745/",
    },
    "1196475": {
        "tour": "cairo",
        "location_path": "cairo-l92",
        "display_name": "Hurghada to Cairo: Pyramids & Museum for First-Time Visitors",
        "url": "https://www.getyourguide.com/cairo-l92/hurghada-to-cairo-pyramids-museum-for-first-time-visitors-t1196475/",
    },
    "1195743": {
        "tour": "cairoQuad",
        "location_path": "cairo-l92",
        "display_name": "Hurghada: Cairo Day Trip with Pyramids, Museum & Quad Bike",
        "url": "https://www.getyourguide.com/cairo-l92/hurghada-cairo-day-trip-with-pyramids-museum-quad-bike-t1195743/",
    },
    "1289272": {
        "tour": "cairo2day",
        "location_path": "cairo-l92",
        "display_name": "Hurghada: Cairo 2-Day Tour with Luxury Pyramids View Stay",
        "url": "https://www.getyourguide.com/cairo-l92/hurghada-cairo-2-day-tour-with-luxury-pyramids-view-stay-t1289272/",
    },
    "1289286": {
        "tour": "hiddenCairo",
        "location_path": "cairo-l92",
        "display_name": "From Hurghada: Hidden Cairo, Pyramids & Cave Church",
        "url": "https://www.getyourguide.com/cairo-l92/from-hurghada-hidden-cairo-pyramids-cave-church-t1289286/",
    },
    "1303745": {
        "tour": "luxorKarnak",
        "location_path": "luxor-l109",
        "display_name": "Hurghada: Luxor Karnak, Hatshepsut & Valley of the Kings",
        "url": "https://www.getyourguide.com/luxor-l109/hurghada-luxor-karnak-hatshepsut-valley-of-the-kings-t1303745/",
    },
    # Sharm
    "1195076": {
        "tour": "blueHole",
        "location_path": "dahab-l884",
        "display_name": "Sharm: Jeep Adventure to Blue Hole, Canyon & Dahab",
        "url": "https://www.getyourguide.com/dahab-l884/sharm-el-sheikh-jeep-adventure-to-blue-hole-canyon-dahab-t1195076/",
    },
    "1278027": {
        "tour": "dahab3pools",
        "location_path": "dahab-l884",
        "display_name": "Sharm: 3 Pools Dahab, Quad, Camel, Red Canyon & Lunch",
        "url": "https://www.getyourguide.com/dahab-l884/sharm-3-pools-dahab-quad-camel-red-canyon-lunch-t1278027/",
    },
    "1286076": {
        "tour": "rasMohamed",
        "location_path": "sharm-el-sheikh-l174",
        "display_name": "Ras Mohamed Half-Day Adventure",
        "url": "https://www.getyourguide.com/sharm-el-sheikh-l174/ras-mohamed-half-day-adventure-t1286076/",
    },
    "1366559": {
        "tour": "vipDesert",
        "location_path": "sharm-el-sheikh-l174",
        "display_name": "VIP Sharm Desert Escape",
        "url": "https://www.getyourguide.com/sharm-el-sheikh-l174/vip-sharm-desert-escape-t1366559/",
    },
    "1344400": {
        "tour": "sharmCairo2day",
        "location_path": "cairo-l92",
        "display_name": "Sharm: Cairo 2-Day with Luxury Pyramids View Stay",
        "url": "https://www.getyourguide.com/cairo-l92/sharm-cairo-2-day-with-luxury-pyramids-view-stay-t1344400/",
    },
    "1273778": {
        "tour": "sharmCairoBus",
        "location_path": "cairo-l92",
        "display_name": "Discover Cairo, Great Pyramids & Quad Bike From Sharm By Bus",
        "url": "https://www.getyourguide.com/cairo-l92/discover-cairo-great-pyramids-quad-bike-from-sharm-by-bus-t1273778/",
    },
    # Bonus products
    BONUS_HURGHADA_CITY_TOUR: {
        "tour": "cityTour",
        "location_path": "hurghada-l403",
        "display_name": "Hurghada City Tour",
        "url": "https://www.getyourguide.com/hurghada-l403/hurghada-uncoveredcity-tour-bazaar-sand-museum-experience-t1279014/",
    },
    BONUS_SHARM_SIGNATURE: {
        "tour": "sharmSignature",
        "location_path": "sharm-el-sheikh-l174",
        "display_name": "Sharm Signature",
        "url": "",
    },
}

# Booked Product ID -> paid offer Product ID + complimentary bonus Product ID
DEFAULT_OFFER_ROUTES: Dict[str, Dict[str, str]] = {
    # Hurghada Luxor family -> Cairo by plane + City Tour FREE
    "1191624": {"offer_product_id": "1195745", "bonus_product_id": BONUS_HURGHADA_CITY_TOUR},
    "1303745": {"offer_product_id": "1195745", "bonus_product_id": BONUS_HURGHADA_CITY_TOUR},
    # Hurghada Cairo family -> Luxor + City Tour FREE
    "1195745": {"offer_product_id": "1191624", "bonus_product_id": BONUS_HURGHADA_CITY_TOUR},
    "1196475": {"offer_product_id": "1191624", "bonus_product_id": BONUS_HURGHADA_CITY_TOUR},
    "1195743": {"offer_product_id": "1191624", "bonus_product_id": BONUS_HURGHADA_CITY_TOUR},
    "1289272": {"offer_product_id": "1191624", "bonus_product_id": BONUS_HURGHADA_CITY_TOUR},
    "1289286": {"offer_product_id": "1191624", "bonus_product_id": BONUS_HURGHADA_CITY_TOUR},
    # Sharm adventure family -> Cairo 2-day + Signature FREE
    "1195076": {"offer_product_id": "1344400", "bonus_product_id": BONUS_SHARM_SIGNATURE},
    "1278027": {"offer_product_id": "1344400", "bonus_product_id": BONUS_SHARM_SIGNATURE},
    "1286076": {"offer_product_id": "1344400", "bonus_product_id": BONUS_SHARM_SIGNATURE},
    "1366559": {"offer_product_id": "1344400", "bonus_product_id": BONUS_SHARM_SIGNATURE},
    # Sharm Cairo family -> Blue Hole + Signature FREE
    "1344400": {"offer_product_id": "1195076", "bonus_product_id": BONUS_SHARM_SIGNATURE},
    "1273778": {"offer_product_id": "1195076", "bonus_product_id": BONUS_SHARM_SIGNATURE},
}

_REDIRECT_PREFIXES = (
    "https://redirect.ftstravels.com/",
    "http://redirect.ftstravels.com/",
    "https://redirect.ftstravels.net/",
    "http://redirect.ftstravels.net/",
    "https://redirect-tour.netlify.app/",
    "http://redirect-tour.netlify.app/",
)


def _clean_str(v: Any) -> str:
    return str(v or "").strip()


def _row_value(row: Any, key: str) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, None)


def _clean_phone(v: Any) -> str:
    return re.sub(r"\D", "", _clean_str(v))


def _short_name(full_name: str) -> str:
    s = _clean_str(full_name)
    parts = [p for p in s.split() if p.strip()]
    if not parts:
        return "Guest"
    return " ".join(parts[:2])


def _select_email(fields: Dict[str, Any], agent) -> str:
    personal = _clean_str(agent.get_field_value(fields, FieldIds.CUSTOMER_PERSONAL_EMAIL))
    if personal and "@" in personal:
        return personal
    primary = _clean_str(agent.get_field_value(fields, FieldIds.CUSTOMER_EMAIL))
    if primary and "@" in primary:
        return primary
    for key in ("Customer personal email", "Customer Email", "Customer Email "):
        val = _clean_str(fields.get(key))
        if val and "@" in val:
            return val
    return ""


def _normalize_product_entry(entry: Any) -> Optional[Dict[str, str]]:
    if isinstance(entry, dict):
        return {
            "tour": _clean_str(entry.get("tour")),
            "display_name": _clean_str(entry.get("display_name") or entry.get("name")),
            "url": _clean_str(entry.get("url") or entry.get("gyg_url")),
            "location_path": _clean_str(entry.get("location_path") or entry.get("location")),
        }
    if isinstance(entry, (tuple, list)) and len(entry) >= 2:
        return {
            "tour": _clean_str(entry[0]),
            "display_name": "",
            "url": _clean_str(entry[1]),
            "location_path": "",
        }
    return None


def resolve_offer_product(
    product_id: Any,
    product_map: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, str]]:
    """
    Resolve product_id -> {product_id, tour, display_name, url, location_path}.
    Returns None if unknown.
    """
    pid = _clean_str(product_id)
    if not pid:
        return None
    mapping = product_map if isinstance(product_map, dict) and product_map else DEFAULT_OFFER_PRODUCTS
    entry = _normalize_product_entry(mapping.get(pid))
    if not entry:
        return None
    if not entry.get("tour") and not entry.get("url") and not entry.get("display_name"):
        return None
    return {
        "product_id": pid,
        "tour": entry.get("tour") or "",
        "display_name": entry.get("display_name") or entry.get("tour") or pid,
        "url": entry.get("url") or "",
        "location_path": entry.get("location_path") or "",
    }


def _slugify_gyg_name(name: Any) -> str:
    """Convert productName into GetYourGuide URL slug segment."""
    s = _clean_str(name).lower()
    if not s:
        return ""
    s = s.replace("&", " ")
    s = s.replace("'", "")
    s = s.replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")


def _location_path_from_url(url: Any) -> str:
    m = re.match(r"https?://(?:www\.)?getyourguide\.com/([^/?#]+)/", _clean_str(url), flags=re.I)
    return _clean_str(m.group(1)) if m else ""


def build_dynamic_gyg_url(
    product_id: Any,
    product_name: Any = None,
    location_path: Any = None,
    fallback_url: Any = None,
) -> str:
    """
    Build GYG activity URL dynamically from Analytics name:
      https://www.getyourguide.com/{location}/{slug(name)}-t{productId}/
    Falls back to known static URL when name/location are missing.
    """
    pid = _extract_product_id(product_id)
    fallback = _clean_str(fallback_url)
    loc = _clean_str(location_path) or _location_path_from_url(fallback)
    slug = _slugify_gyg_name(product_name)

    if pid and loc and slug:
        return f"https://www.getyourguide.com/{loc}/{slug}-t{pid}/"
    if fallback:
        return fallback
    if pid:
        return f"https://www.getyourguide.com/s/?q=t{pid}"
    return ""


def _extract_product_id(raw: Any) -> str:
    """Normalize Product ID from Airtable (may be multiline / mixed text)."""
    s = _clean_str(raw)
    if not s:
        return ""
    m = re.search(r"\d{6,}", s)
    if m:
        return m.group(0)
    return s.split()[0] if s.split() else s


def get_product_display_name(
    product_id: Any,
    product_map: Optional[Dict[str, Any]] = None,
    fallback: str = "",
) -> str:
    resolved = resolve_offer_product(product_id, product_map)
    if resolved and resolved.get("display_name"):
        return resolved["display_name"]
    return _clean_str(fallback) or _clean_str(product_id)


def resolve_offer_route(
    booked_product_id: Any = None,
    trip_name: Any = None,
    routes: Optional[Dict[str, Dict[str, str]]] = None,
) -> Optional[Dict[str, str]]:
    """
    Resolve cross-sell route primarily by booked Product ID.
    Fallback: legacy trip-name keywords (luxor/cairo) for older records.
    Returns {route_key, booked_product_id, offer_product_id, bonus_product_id}.
    """
    route_map = routes if isinstance(routes, dict) and routes else DEFAULT_OFFER_ROUTES
    pid = _extract_product_id(booked_product_id)
    if pid and pid in route_map:
        cfg = route_map.get(pid) or {}
        offer_pid = _clean_str(cfg.get("offer_product_id"))
        bonus_pid = _clean_str(cfg.get("bonus_product_id"))
        if offer_pid:
            return {
                "route_key": pid,
                "booked_product_id": pid,
                "offer_product_id": offer_pid,
                "bonus_product_id": bonus_pid,
            }

    t = _clean_str(trip_name).lower()
    if "luxor" in t:
        legacy_pid = "1191624"
    elif "cairo" in t:
        legacy_pid = "1196475"
    else:
        return None
    if legacy_pid in route_map:
        cfg = route_map.get(legacy_pid) or {}
        offer_pid = _clean_str(cfg.get("offer_product_id"))
        bonus_pid = _clean_str(cfg.get("bonus_product_id"))
        if offer_pid:
            return {
                "route_key": f"name:{legacy_pid}",
                "booked_product_id": pid or legacy_pid,
                "offer_product_id": offer_pid,
                "bonus_product_id": bonus_pid,
            }
    return None


def _get_gyg_analytics_table(agent):
    try:
        api = getattr(agent, "airtable_api", None)
        base_id = getattr(agent, "base_id", None)
        if not api or not base_id:
            return None
        return api.table(base_id, GYG_ANALYTICS_TABLE)
    except Exception as e:
        logging.warning(f"GYG Analytics table unavailable: {e}")
        return None


def lookup_gyg_analytics_name(agent, product_id: Any, cache: Optional[Dict[str, str]] = None) -> str:
    """Lookup productName from Airtable GYG Analytics by productId."""
    pid = _extract_product_id(product_id)
    if not pid:
        return ""
    if isinstance(cache, dict) and pid in cache:
        return _clean_str(cache.get(pid))
    name = ""
    try:
        table = _get_gyg_analytics_table(agent)
        if table is not None:
            from pyairtable.formulas import match

            recs = table.all(formula=match({"productId": pid}), max_records=1)
            if recs:
                name = _clean_str((recs[0].get("fields") or {}).get("productName"))
    except Exception as e:
        logging.warning(f"GYG Analytics lookup failed for {pid}: {e}")
    if isinstance(cache, dict):
        cache[pid] = name
    return name


def enrich_product_from_agent(
    agent,
    product_id: Any,
    product_map: Optional[Dict[str, Any]] = None,
    analytics_cache: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Merge static catalog + GYG Analytics name, then rebuild GYG URL when the
    Analytics productName changes. If the name is unchanged/missing, keep the
    known-good catalog URL (preserves GYG slug quirks like uncoveredcity).
    """
    pid = _extract_product_id(product_id)
    base = resolve_offer_product(pid, product_map) or {
        "product_id": pid,
        "tour": "",
        "display_name": "",
        "url": "",
        "location_path": "",
    }
    catalog_name = _clean_str(base.get("display_name"))
    fallback_url = _clean_str(base.get("url"))
    location_path = _clean_str(base.get("location_path")) or _location_path_from_url(fallback_url)

    analytics_name = lookup_gyg_analytics_name(agent, pid, analytics_cache)
    json_title = ""
    json_url = ""

    try:
        gyg_map = getattr(agent, "gyg_data_map", None) or {}
        trip = gyg_map.get(str(pid)) if isinstance(gyg_map, dict) else None
        if isinstance(trip, dict):
            for key in ("url", "gyg_url", "link", "product_url"):
                u = _clean_str(trip.get(key))
                if u.startswith("http"):
                    json_url = u
                    break
            json_title = _clean_str(trip.get("title") or trip.get("name") or trip.get("product_name"))
    except Exception:
        pass

    live_name = analytics_name or json_title or catalog_name
    if live_name:
        base["display_name"] = live_name

    if not location_path and json_url:
        location_path = _location_path_from_url(json_url)

    name_changed = bool(
        analytics_name
        and catalog_name
        and _slugify_gyg_name(analytics_name) != _slugify_gyg_name(catalog_name)
    )

    if name_changed:
        # Product renamed in GYG Analytics → rebuild slug from the new name
        base["url"] = build_dynamic_gyg_url(
            pid,
            product_name=analytics_name,
            location_path=location_path,
            fallback_url=fallback_url or json_url,
        )
    else:
        # Keep verified catalog/JSON URL; still allow dynamic build if no fallback
        base["url"] = (
            fallback_url
            or json_url
            or build_dynamic_gyg_url(
                pid,
                product_name=live_name,
                location_path=location_path,
                fallback_url="",
            )
        )

    base["location_path"] = location_path
    if not base.get("display_name"):
        base["display_name"] = pid
    return base


def build_offer_redirect_url(
    booking_nr: Any,
    phone: Any,
    product_id: Any,
    tour_key: Optional[str] = None,
    gyg_url: Optional[str] = None,
    product_map: Optional[Dict[str, Any]] = None,
    redirect_base: Optional[str] = None,
) -> str:
    """
    Build tracking redirect URL:
    https://redirect.ftstravels.com/?bookingNr=...&tour=...&redirect=<GYG>&phone=...&productId=...
    """
    base = _clean_str(redirect_base) or REDIRECT_BASE
    if not base.endswith("/"):
        base = base + "/"

    resolved = resolve_offer_product(product_id, product_map)
    pid = _extract_product_id(product_id)
    if resolved:
        pid = resolved["product_id"]
        tour = _clean_str(tour_key) or resolved.get("tour") or ""
        dest = _clean_str(gyg_url) or resolved.get("url") or ""
    else:
        tour = _clean_str(tour_key)
        dest = _clean_str(gyg_url)

    if not dest and pid:
        dest = f"https://www.getyourguide.com/s/?q=t{pid}"

    if not dest:
        return ""

    params = {
        "bookingNr": _clean_str(booking_nr) or "",
        "tour": tour or "Unknown",
        "redirect": dest,
        "phone": _clean_phone(phone),
    }
    if pid:
        params["productId"] = pid

    query = urlencode(params, quote_via=quote)
    return f"{base}?{query}"


def _make_redirect_param(full_url: str) -> str:
    u = _clean_str(full_url)
    if not u:
        return ""
    for p in _REDIRECT_PREFIXES:
        if u.startswith(p):
            return u[len(p) :]
    for host in (
        "redirect.ftstravels.com/",
        "redirect.ftstravels.net/",
        "redirect-tour.netlify.app/",
    ):
        if u.startswith(host):
            return u[len(host) :]
    return u


def _parse_iso_datetime(value: Any) -> Optional[datetime]:
    s = _clean_str(value)
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _get_recent_offer_attempt(agent, booking_nr: str, within_minutes: int) -> Optional[Dict[str, Any]]:
    booking_nr = _clean_str(booking_nr)
    if not booking_nr or within_minutes <= 0:
        return None
    try:
        import chat_db

        cutoff_dt = datetime.now(timezone.utc) - timedelta(minutes=int(within_minutes))
        cutoff_iso = cutoff_dt.isoformat()
        with sqlite3.connect(chat_db.DB_FILE, timeout=15.0) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(
                """
                SELECT m.timestamp, m.status, m.text, c.chat_id
                FROM messages m
                JOIN conversations c ON c.chat_id = m.chat_id
                WHERE c.booking_number = ?
                  AND m.source = 'WhatsApp'
                  AND m.text LIKE ?
                  AND m.timestamp >= ?
                ORDER BY m.timestamp DESC
                LIMIT 1
                """,
                (booking_nr, "%Offer Send FTS Template Sent%", cutoff_iso),
            )
            row = c.fetchone()
            if not row:
                return None
            return {
                "timestamp": _clean_str(row["timestamp"]),
                "status": _clean_str(row["status"]) or "unknown",
                "chat_id": _clean_str(row["chat_id"]),
            }
    except Exception as e:
        logging.warning(f"Offer Send FTS cooldown lookup failed for {booking_nr}: {e}")
        return None


def _ensure_chat(
    agent,
    record_id: str,
    customer_name_short: str,
    customer_email: str,
    to_phone: str,
    booking_nr: str,
    location: str = "Hurghada/Cairo",
):
    try:
        import chat_db

        chat_id = None
        receiving_phone_id = None

        existing_conv = chat_db.get_chat_by_record_id(record_id)
        if existing_conv:
            chat_id = _clean_str(_row_value(existing_conv, "chat_id")) or None
            receiving_phone_id = _clean_str(_row_value(existing_conv, "receiving_phone_id")) or None

        if not chat_id:
            if _clean_str(to_phone):
                identifier = _clean_str(to_phone)
                source = "WhatsApp"
            elif _clean_str(customer_email):
                identifier = _clean_str(customer_email)
                source = "Email"
            else:
                identifier = _clean_str(booking_nr) or _clean_str(record_id)
                source = "WhatsApp"

            conv = chat_db.get_or_create_conversation(
                source=source,
                sender_identifier=identifier,
                contact_name=customer_name_short or "Guest",
                airtable_record_id=record_id,
                location=_clean_str(location) or "Hurghada/Cairo",
                thread_id="",
                receiving_phone_id=receiving_phone_id or "",
            )
            chat_id = _clean_str((conv or {}).get("chat_id")) or None

        if chat_id:
            try:
                chat_db.update_conversation_info(chat_id, booking_number=booking_nr)
            except Exception:
                pass

        return chat_id, receiving_phone_id
    except Exception:
        return None, None


def _log_whatsapp(
    agent,
    record_id: str,
    customer_name_short: str,
    customer_email: str,
    to_phone: str,
    booking_nr: str,
    template_name: str,
    wa_ok: bool,
    wa_meta: Optional[Dict[str, Any]],
    fallback_text: str,
    location: str = "Hurghada/Cairo",
):
    try:
        import chat_db

        chat_id, _ = _ensure_chat(
            agent,
            record_id,
            customer_name_short,
            customer_email,
            to_phone,
            booking_nr,
            location=location,
        )
        if not chat_id:
            return
        message_id = None
        template_text = ""
        if isinstance(wa_meta, dict):
            message_id = wa_meta.get("message_id")
            template_text = _clean_str(wa_meta.get("template_text"))
        err_body = ""
        if isinstance(wa_meta, dict) and not wa_ok:
            err_body = _clean_str(wa_meta.get("body"))
        header = f"[Sent WhatsApp] Offer Send FTS Template Sent ({template_name})"
        if err_body == "GIFT_BOUNCE_TEMPLATE_MISCONFIGURED_AS_CANCEL_RECOVERY":
            header = "[Sent WhatsApp] Offer Send FTS BLOCKED — gift_bounce Meta template has Cancel Recovery text"
        txt = f"{header}\n{template_text or fallback_text}"
        chat_db.add_message(
            chat_id=chat_id,
            sender_type="agent",
            text=txt,
            status="sent" if wa_ok else "error",
            increment_unread=False,
            source="WhatsApp",
            external_message_id=message_id,
        )
    except Exception:
        pass


def _mark_offer_processed(
    agent,
    record_id: str,
    booking_nr: str,
    offer_status_field: str,
    follow_sales_field: str,
    clear_follow_sales: bool,
    wa_ok: bool,
) -> Dict[str, Any]:
    """
    Always mark Offer Send Status after an attempt (success or failure)
    so the record leaves the Airtable view and is not re-sent.
    Clear Follow sales in a separate update so a collaborator clear
    failure cannot block the status checkbox update.
    """
    out = {
        "status_updated": False,
        "follow_sales_cleared": False,
        "error": None,
    }
    status_field = _clean_str(offer_status_field) or "Offer Send Status"

    try:
        if hasattr(agent, "update_booking_record"):
            agent.update_booking_record(record_id, {status_field: True})
        else:
            agent.table.update(record_id, {status_field: True})
        out["status_updated"] = True
    except Exception as e:
        out["error"] = f"status_update_failed: {e}"
        logging.error(
            "Offer Send FTS failed to set %s for %s (%s): %s",
            status_field,
            booking_nr or record_id,
            "success" if wa_ok else "error",
            e,
            exc_info=True,
        )
        return out

    if clear_follow_sales and _clean_str(follow_sales_field):
        try:
            if hasattr(agent, "update_booking_record"):
                agent.update_booking_record(record_id, {follow_sales_field: None})
            else:
                agent.table.update(record_id, {follow_sales_field: None})
            out["follow_sales_cleared"] = True
        except Exception as e:
            logging.warning(
                "Offer Send FTS status saved but failed clearing %s for %s: %s",
                follow_sales_field,
                booking_nr or record_id,
                e,
            )
            if not out["error"]:
                out["error"] = f"follow_sales_clear_failed: {e}"

    return out


def run(agent, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = payload or {}
    view = _clean_str(payload.get("view")) or "Offer Get Your Guide"
    max_records = int(payload.get("max_records") or 10)
    dry_run = bool(payload.get("dry_run", False))
    template_language = _clean_str(payload.get("template_language")) or "en"
    clear_follow_sales = bool(payload.get("clear_follow_sales", True))
    follow_sales_field = _clean_str(payload.get("follow_sales_field")) or "Follow sales"
    offer_status_field = _clean_str(payload.get("offer_status_field")) or "Offer Send Status"
    retry_cooldown_minutes = int(payload.get("retry_cooldown_minutes") or 180)

    # gift_bounce: Hi {{1}} / booked {{2}} / offer {{3}} / bonus {{4}} + 1 dynamic URL button
    # Prefer explicit template_name. Ignore legacy template_gift1/gift2 so old
    # workflow bodies cannot accidentally keep sending gift1.
    template_name = _clean_str(payload.get("template_name")) or DEFAULT_TEMPLATE_NAME
    if template_name in ("gift1", "gift2"):
        logging.warning(
            "Offer Send FTS ignoring legacy template_name=%s; using %s",
            template_name,
            DEFAULT_TEMPLATE_NAME,
        )
        template_name = DEFAULT_TEMPLATE_NAME
    redirect_base = _clean_str(payload.get("redirect_base")) or REDIRECT_BASE

    product_map = DEFAULT_OFFER_PRODUCTS
    if isinstance(payload.get("products"), dict) and payload.get("products"):
        # Shallow merge so payload can override display names / URLs
        product_map = {**DEFAULT_OFFER_PRODUCTS, **payload["products"]}

    route_map = DEFAULT_OFFER_ROUTES
    if isinstance(payload.get("routes"), dict) and payload.get("routes"):
        route_map = {**DEFAULT_OFFER_ROUTES, **payload["routes"]}

    # Optional full-URL override for the single CTA (supports {booking_nr}/{phone})
    button_url_override = _clean_str(payload.get("button_url") or payload.get("gift_button_0"))
    analytics_cache: Dict[str, str] = {}

    records = agent.table.all(
        view=view,
        max_records=max_records,
        fields=[
            "Booking Nr.",
            "Product ID",
            "trip Name",
            "Customer Name",
            "Customer Phone",
            "Offer Send Status",
            "Customer Email",
            "Customer personal email",
            "Follow sales",
            "des",
        ],
    )

    results: List[Dict[str, Any]] = []
    sent_whatsapp = 0
    updated = 0

    for rec in records or []:
        rid = _clean_str((rec or {}).get("id"))
        fields = (rec or {}).get("fields", {}) or {}
        if not rid:
            continue

        booking_nr = _clean_str(agent.get_field_value(fields, FieldIds.BOOKING_NR) or fields.get("Booking Nr."))
        trip_name = _clean_str(agent.get_field_value(fields, FieldIds.TRIP_NAME) or fields.get("trip Name"))
        booked_product_id = _extract_product_id(
            agent.get_field_value(fields, FieldIds.PRODUCT_ID) or fields.get("Product ID")
        )
        customer_name = _clean_str(agent.get_field_value(fields, FieldIds.CUSTOMER_NAME) or fields.get("Customer Name")) or "Guest"
        customer_phone = _clean_phone(agent.get_field_value(fields, FieldIds.CUSTOMER_PHONE) or fields.get("Customer Phone"))
        customer_email = _select_email(fields, agent)
        short_name = _short_name(customer_name)
        destination = _clean_str(fields.get("des") or fields.get("Des") or "")

        already_sent = fields.get(offer_status_field)
        if already_sent is True or str(already_sent or "").strip().lower() in ("true", "1", "yes", "done"):
            results.append({"record_id": rid, "status": "skipped", "booking_nr": booking_nr, "message": "already_sent"})
            continue

        recent_attempt = _get_recent_offer_attempt(agent, booking_nr, retry_cooldown_minutes)
        if recent_attempt:
            # Previous attempt already happened (often a failed WhatsApp send) but
            # Airtable status may never have been marked. Mark it now so the
            # record leaves the view without another outbound message.
            mark_info = _mark_offer_processed(
                agent,
                rid,
                booking_nr,
                offer_status_field,
                follow_sales_field,
                clear_follow_sales,
                str(recent_attempt.get("status") or "").lower() == "sent",
            )
            if mark_info.get("status_updated"):
                updated += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "booking_nr": booking_nr,
                    "message": "recent_attempt_cooldown",
                    "last_attempt_at": recent_attempt.get("timestamp"),
                    "last_attempt_status": recent_attempt.get("status"),
                    "retry_cooldown_minutes": retry_cooldown_minutes,
                    "airtable_status_updated": bool(mark_info.get("status_updated")),
                    "follow_sales_cleared": bool(mark_info.get("follow_sales_cleared")),
                    "airtable_update_error": mark_info.get("error"),
                }
            )
            continue

        route = resolve_offer_route(
            booked_product_id=booked_product_id,
            trip_name=trip_name,
            routes=route_map,
        )
        if not route:
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "booking_nr": booking_nr,
                    "product_id": booked_product_id,
                    "message": "no_matching_route",
                }
            )
            continue

        if not customer_phone:
            results.append({"record_id": rid, "status": "error", "booking_nr": booking_nr, "message": "missing_phone"})
            continue

        offer_pid = route["offer_product_id"]
        bonus_pid = route.get("bonus_product_id") or ""
        booked_meta = enrich_product_from_agent(
            agent,
            route.get("booked_product_id") or booked_product_id,
            product_map=product_map,
            analytics_cache=analytics_cache,
        )
        offer_meta = enrich_product_from_agent(
            agent,
            offer_pid,
            product_map=product_map,
            analytics_cache=analytics_cache,
        )
        bonus_meta = enrich_product_from_agent(
            agent,
            bonus_pid,
            product_map=product_map,
            analytics_cache=analytics_cache,
        )

        if not offer_meta.get("url"):
            results.append(
                {
                    "record_id": rid,
                    "status": "error",
                    "booking_nr": booking_nr,
                    "message": "missing_offer_product_url",
                    "offer_product_id": offer_pid,
                }
            )
            continue

        offer_display = offer_meta.get("display_name") or offer_pid
        bonus_display = bonus_meta.get("display_name") or get_product_display_name(
            bonus_pid, product_map, fallback="complimentary experience"
        )
        booked_display = (
            trip_name
            or booked_meta.get("display_name")
            or booked_product_id
            or "your trip"
        )

        if button_url_override:
            btn_full = button_url_override.format(booking_nr=booking_nr, phone=customer_phone)
        else:
            btn_full = build_offer_redirect_url(
                booking_nr,
                customer_phone,
                offer_pid,
                tour_key=offer_meta.get("tour"),
                gyg_url=offer_meta.get("url"),
                product_map=product_map,
                redirect_base=redirect_base,
            )

        if not btn_full:
            results.append(
                {
                    "record_id": rid,
                    "status": "error",
                    "booking_nr": booking_nr,
                    "message": "failed_build_redirect_url",
                    "offer_product_id": offer_pid,
                }
            )
            continue

        button_url_params = [_make_redirect_param(btn_full)]
        structured_vars = {
            "body": [short_name, booked_display, offer_display, bonus_display],
            "button_url": button_url_params,
        }
        fallback_text = "\n".join(
            [
                f"Hi {short_name}",
                f"Thank you for booking {booked_display} with us through GetYourGuide.",
                f"Book {offer_display} through GetYourGuide and enjoy {bonus_display} FREE.",
                btn_full,
            ]
        )

        # WhatsApp location: Sharm bonus routes use Sharm sender when destination hints Sharm
        wa_location = "Hurghada/Cairo"
        dest_l = destination.lower()
        offer_l = (offer_display or "").lower()
        if "sharm" in dest_l or "sharm" in offer_l or bonus_pid == BONUS_SHARM_SIGNATURE:
            wa_location = "Sharm"

        if dry_run:
            results.append(
                {
                    "record_id": rid,
                    "status": "dry_run",
                    "booking_nr": booking_nr,
                    "product_id": booked_product_id,
                    "template_name": template_name,
                    "route_key": route.get("route_key"),
                    "offer_product_id": offer_pid,
                    "bonus_product_id": bonus_pid,
                    "body_vars": structured_vars["body"],
                    "button_params": button_url_params,
                    "whatsapp_location": wa_location,
                }
            )
            continue

        wa_ok, wa_meta = agent.send_whatsapp_message(
            customer_phone,
            text="",
            location=wa_location,
            template_name=template_name,
            template_language=template_language,
            booking_data=fields,
            template_variables=structured_vars,
        )
        sent_whatsapp += 1 if wa_ok else 0
        _log_whatsapp(
            agent,
            rid,
            short_name,
            customer_email,
            customer_phone,
            booking_nr,
            template_name,
            bool(wa_ok),
            wa_meta if isinstance(wa_meta, dict) else None,
            fallback_text,
            location=wa_location,
        )

        # Mark processed on BOTH success and failure so the Airtable view
        # filter removes the record and we do not keep re-sending offers.
        mark_info = _mark_offer_processed(
            agent,
            rid,
            booking_nr,
            offer_status_field,
            follow_sales_field,
            clear_follow_sales,
            bool(wa_ok),
        )
        if mark_info.get("status_updated"):
            updated += 1

        results.append(
            {
                "record_id": rid,
                "status": "success" if wa_ok else "error",
                "booking_nr": booking_nr,
                "product_id": booked_product_id,
                "template_name": template_name,
                "route_key": route.get("route_key"),
                "offer_product_id": offer_pid,
                "bonus_product_id": bonus_pid,
                "whatsapp_ok": bool(wa_ok),
                "whatsapp_location": wa_location,
                "airtable_status_updated": bool(mark_info.get("status_updated")),
                "follow_sales_cleared": bool(mark_info.get("follow_sales_cleared")),
                "airtable_update_error": mark_info.get("error"),
            }
        )

    return {
        "status": "success",
        "data": {
            "view": view,
            "template_name": template_name,
            "redirect_base": redirect_base,
            "retry_cooldown_minutes": retry_cooldown_minutes,
            "dry_run": dry_run,
            "processed": len(results),
            "sent_whatsapp": sent_whatsapp,
            "updated": updated,
            "results": results,
        },
    }
