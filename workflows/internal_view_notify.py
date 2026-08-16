"""
Internal Notifications — Airtable view poller (Make.com replacement).

Dedup rules (strict — never send the same alert twice):
  1) Atomic claim in SQLite BEFORE WhatsApp send (survives concurrent schedule threads).
  2) Global key across scenarios: record_id + phone + alert_kind
     (so overlapping Airtable views cannot double-notify the same phone).
  3) Secondary key: booking_nr + phone + alert_kind when booking number exists.
  4) Per-scenario in-process lock to serialize runs of the same workflow.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import time
from datetime import datetime

from fts_paths import get_data_path

log = logging.getLogger("InternalViewNotify")

SCENARIOS_PATH = os.path.join(get_data_path("workflows"), "internal_notification_scenarios.json")
STATE_PREFIX = "int_notify_seen:"
DEDUP_DB = get_data_path("internal_notify_dedup.db")
MAX_SEEN = 4000

_scenario_locks = {}
_scenario_locks_guard = threading.Lock()
_db_init_lock = threading.Lock()
_db_ready = False


def _scenario_lock(scenario_id: str) -> threading.Lock:
    key = str(scenario_id or "_default").strip() or "_default"
    with _scenario_locks_guard:
        lock = _scenario_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _scenario_locks[key] = lock
        return lock


def _ensure_dedup_db():
    global _db_ready
    if _db_ready:
        return
    with _db_init_lock:
        if _db_ready:
            return
        conn = sqlite3.connect(DEDUP_DB, timeout=30.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=30000;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notify_claims (
                    dedup_key TEXT PRIMARY KEY,
                    record_id TEXT,
                    booking_nr TEXT,
                    phone TEXT,
                    alert_kind TEXT,
                    scenario_id TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_notify_claims_record ON notify_claims(record_id, phone, alert_kind)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_notify_claims_booking ON notify_claims(booking_nr, phone, alert_kind)"
            )
            conn.commit()
            _db_ready = True
        finally:
            conn.close()


def _claim_send(record_id: str, booking_nr: str, phone: str, alert_kind: str, scenario_id: str) -> bool:
    """
    Atomically claim the right to send this alert.
    Returns True only for the first claim (caller may send).
    Returns False if already claimed (skip send).
    """
    _ensure_dedup_db()
    rid = str(record_id or "").strip()
    phone_n = _norm_phone(phone)
    kind = str(alert_kind or "last_minute").strip().lower() or "last_minute"
    booking = str(booking_nr or "").strip()
    if not phone_n or (not rid and not booking):
        return False

    keys = []
    if rid:
        keys.append(f"rec|{rid}|{phone_n}|{kind}")
    if booking:
        keys.append(f"bk|{booking.lower()}|{phone_n}|{kind}")
    if not keys:
        return False

    now = datetime.utcnow().isoformat()
    conn = sqlite3.connect(DEDUP_DB, timeout=30.0)
    try:
        conn.execute("PRAGMA busy_timeout=30000;")
        # If ANY related key already exists, treat as already sent.
        for key in keys:
            row = conn.execute("SELECT 1 FROM notify_claims WHERE dedup_key = ? LIMIT 1", (key,)).fetchone()
            if row:
                return False

        try:
            conn.execute("BEGIN IMMEDIATE")
            # Re-check under write lock
            for key in keys:
                row = conn.execute("SELECT 1 FROM notify_claims WHERE dedup_key = ? LIMIT 1", (key,)).fetchone()
                if row:
                    conn.execute("ROLLBACK")
                    return False
            for key in keys:
                conn.execute(
                    """
                    INSERT INTO notify_claims
                        (dedup_key, record_id, booking_nr, phone, alert_kind, scenario_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (key, rid, booking, phone_n, kind, str(scenario_id or ""), now),
                )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            return False
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
    finally:
        conn.close()


def _load_scenarios():
    try:
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return list(data.get("scenarios") or [])
    except Exception as e:
        log.error("Failed to load scenarios: %s", e)
        return []


def _find_scenario(scenario_id: str):
    sid = str(scenario_id or "").strip()
    if not sid:
        return None
    for s in _load_scenarios():
        if str(s.get("id") or "").strip() == sid:
            return s
    return None


def _norm_phone(raw) -> str:
    s = str(raw or "").strip()
    if "@g.us" in s:
        return s
    digits = re.sub(r"\D", "", s)
    return digits


def _field(fields: dict, *names):
    fields = fields or {}
    for n in names:
        if n in fields and fields.get(n) not in (None, ""):
            return fields.get(n)
    lower_map = {str(k).strip().lower(): v for k, v in fields.items()}
    for n in names:
        key = str(n).strip().lower()
        if key in lower_map and lower_map[key] not in (None, ""):
            return lower_map[key]
    return ""


def _get_cairo_tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Africa/Cairo")
    except Exception:
        pass
    try:
        import pytz
        return pytz.timezone("Africa/Cairo")
    except Exception:
        pass
    from datetime import timezone, timedelta
    # Fallback only — prefer Africa/Cairo via zoneinfo/pytz above.
    return timezone(timedelta(hours=3))


def _fmt_date(raw, agent=None) -> str:
    """
    Format Airtable Date Trip for WhatsApp alerts in Africa/Cairo.

    Airtable often returns date/datetime as UTC ISO (e.g. 2026-08-14T21:00:00.000Z
    for a Cairo calendar day of 2026-08-15). Taking the UTC date part alone shifts
    the day wrong — same bug Make avoided with Format Date + Egypt timezone.
    """
    if agent is not None and hasattr(agent, "get_corrected_trip_date"):
        try:
            _, label = agent.get_corrected_trip_date(str(raw or ""))
            label = str(label or "").strip()
            if label and label.lower() != "unknown date":
                return label
        except Exception:
            pass

    s = str(raw or "").strip()
    if not s:
        return ""
    try:
        clean = s
        if " " in clean and "T" not in clean:
            clean = clean.replace(" ", "T", 1)
        if clean.endswith("Z"):
            clean = clean[:-1] + "+00:00"
        if "T" in clean:
            try:
                dt = datetime.fromisoformat(clean)
            except ValueError:
                dt = datetime.fromisoformat(clean.split(".", 1)[0])
            if dt.tzinfo is None:
                # Naive Airtable datetimes are UTC wall-clock for date fields.
                from datetime import timezone as _tz
                dt = dt.replace(tzinfo=_tz.utc)
            dt_cairo = dt.astimezone(_get_cairo_tz())
            return dt_cairo.strftime("%A, %d %B %Y")
        # Already a plain YYYY-MM-DD calendar date — no TZ shift needed.
        d = datetime.strptime(clean[:10], "%Y-%m-%d")
        return d.strftime("%A, %d %B %Y")
    except Exception:
        if "T" in s:
            return s.split("T", 1)[0]
        return s


def _is_canceled(status) -> bool:
    s = str(status or "").strip().lower()
    return "cancel" in s


def _build_last_minute(fields: dict, include_customer_phone: bool, agent=None) -> str:
    booking_nr = _field(fields, "Booking Nr.", "Booking Nr")
    trip_name = _field(fields, "trip Name", "Trip Name")
    option = _field(fields, "Option")
    date_trip = _fmt_date(_field(fields, "Date Trip"), agent=agent)
    adt = _field(fields, "ADT")
    chd = _field(fields, "CHD")
    std = _field(fields, "STD")
    inf = _field(fields, "Inf", "INF")
    guide = _field(fields, "Guide")
    customer_name = _field(fields, "Customer Name")
    customer_phone = _field(fields, "Customer Phone")
    hotel = str(_field(fields, "Hotel Name") or "").replace("\r", " ").replace("\n", " ").strip()
    lines = [
        "🚨 Last-Minute Booking Alert!",
        "",
        f"🧾 Ref: [{booking_nr}]",
        f"🌊 Trip: [{trip_name}]",
        f"🔘 Option:[{option}]",
        f"🕗 Date: [{date_trip}]",
        f"👥 Pax: [ADT:{adt} | CHD:{chd} | STD:{std} | Inf:{inf}]",
        f"🗣 Guide: [{guide}]",
        f"👥 Customer Name: [{customer_name}]",
    ]
    if include_customer_phone:
        lines.append(f"📞 Customer Phone: [{customer_phone}]")
    lines.append(f"🏨 Pickup Hotel: [{hotel}]")
    return "\n".join(lines).strip()


def _build_cancel(fields: dict, include_customer_phone: bool, agent=None) -> str:
    booking_nr = _field(fields, "Booking Nr.", "Booking Nr")
    trip_name = _field(fields, "trip Name", "Trip Name")
    option = _field(fields, "Option")
    date_trip = _fmt_date(_field(fields, "Date Trip"), agent=agent)
    status = _field(fields, "Booking Status")
    adt = _field(fields, "ADT")
    chd = _field(fields, "CHD")
    std = _field(fields, "STD")
    inf = _field(fields, "Inf", "INF")
    guide = _field(fields, "Guide")
    customer_name = _field(fields, "Customer Name")
    customer_phone = _field(fields, "Customer Phone")
    hotel = str(_field(fields, "Hotel Name") or "").replace("\r", " ").replace("\n", " ").strip()
    lines = [
        "🚨 Cancel Booking Alert!",
        "",
        f"🧾 Ref: [{booking_nr}]",
        f"🌊 Trip: [{trip_name}]",
        f"🔘 Option:[{option}]",
        f"🕗 Date: [{date_trip}]",
        f"🗣 Status: [{status}]",
        f"👥 Pax: [ADT:{adt} | CHD:{chd} | STD:{std} | Inf:{inf}]",
        f"🗣 Guide: [{guide}]",
        f"👥 Customer Name: [{customer_name}]",
    ]
    if include_customer_phone:
        lines.append(f"📞 Customer Phone: [{customer_phone}]")
    lines.append(f"🏨 Pickup Hotel: [{hotel}]")
    return "\n".join(lines).strip()


def _load_seen(agent, scenario_id: str) -> list:
    key = STATE_PREFIX + scenario_id
    try:
        import chat_db
        raw = chat_db.get_setting(key)
        if not raw:
            return []
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data if str(x).strip()]
        if isinstance(data, dict):
            ids = data.get("ids") or []
            return [str(x) for x in ids if str(x).strip()]
    except Exception:
        pass
    return []


def _save_seen(agent, scenario_id: str, ids: list):
    key = STATE_PREFIX + scenario_id
    trimmed = list(dict.fromkeys([str(x).strip() for x in ids if str(x).strip()]))[-MAX_SEEN:]
    try:
        import chat_db
        chat_db.set_setting(
            key,
            json.dumps({"ids": trimmed, "updated_at": datetime.utcnow().isoformat()}, ensure_ascii=False),
        )
    except Exception as e:
        log.error("Failed to save seen state: %s", e)


def _resolve_table(agent, base_id: str, table_id: str, view_label: str):
    default_list = "tblJodXmOWKiYqiXS"
    if table_id == default_list or not table_id:
        table = getattr(agent, "table", None)
        if table is not None:
            return table
    api = getattr(agent, "airtable_api", None)
    if api is None:
        raise Exception("airtable_api_not_configured")
    return api.table(base_id, table_id)


def _send_whatsapp(agent, phone: str, text: str, dry_run: bool):
    phone_n = _norm_phone(phone)
    text = str(text or "").strip()
    if not phone_n or not text:
        return {"phone": phone_n, "ok": False, "error": "missing"}
    if dry_run:
        return {"phone": phone_n, "ok": True, "dry_run": True}

    # Primary only — do NOT chain fallbacks after a successful-looking primary,
    # and do not multi-send across instances (causes duplicates).
    try:
        ok = bool(agent.send_internal_notifications_whatsapp_text(phone_n, text))
        if ok:
            return {"phone": phone_n, "ok": True, "via": "internal_channel"}
        return {"phone": phone_n, "ok": False, "error": "internal_channel_failed"}
    except Exception as e:
        log.warning("agent internal send failed: %s", e)
        return {"phone": phone_n, "ok": False, "error": str(e)}


def run(agent, payload=None):
    payload = payload or {}
    scenario_id = str(payload.get("scenario_id") or "").strip()
    scenario = _find_scenario(scenario_id) if scenario_id else None

    view = str(payload.get("view") or (scenario or {}).get("view_label") or "").strip()
    view_id = str(payload.get("view_id") or (scenario or {}).get("view_id") or "").strip()
    table_id = str(payload.get("table_id") or (scenario or {}).get("table_id") or "tblJodXmOWKiYqiXS").strip()
    base_id = str(payload.get("base_id") or (scenario or {}).get("base_id") or "appTp5YgSp9DV2HYc").strip()
    mode = str(payload.get("mode") or (scenario or {}).get("mode") or "last_minute").strip().lower()
    # Phones from scenarios JSON are the source of truth when scenario_id resolves.
    if scenario is not None:
        phones_raw = scenario.get("phones") or []
    else:
        phones_raw = payload.get("phones")
    # Unique phones only (preserve order)
    phones = []
    for p in phones_raw or []:
        n = _norm_phone(p)
        if n and n not in phones:
            phones.append(n)
    include_customer_phone = payload.get("include_customer_phone")
    if include_customer_phone is None:
        include_customer_phone = bool((scenario or {}).get("include_customer_phone", True))
    else:
        include_customer_phone = bool(include_customer_phone)
    dry_run = bool(payload.get("dry_run", False))
    max_records = int(payload.get("max_records") or 25)
    max_records = max(1, min(max_records, 100))
    state_id = scenario_id or f"view:{view or view_id}"

    if not phones:
        return {"ok": False, "error": "missing_phones", "sent": False}
    if not view and not view_id:
        return {"ok": False, "error": "missing_view", "sent": False}

    lock = _scenario_lock(state_id)
    if not lock.acquire(blocking=False):
        return {
            "ok": True,
            "sent": False,
            "scenario_id": scenario_id,
            "skipped_busy": True,
            "message": "another_run_in_progress",
        }

    try:
        return _run_locked(
            agent=agent,
            payload=payload,
            scenario_id=scenario_id,
            view=view,
            view_id=view_id,
            table_id=table_id,
            base_id=base_id,
            mode=mode,
            phones=phones,
            include_customer_phone=include_customer_phone,
            dry_run=dry_run,
            max_records=max_records,
            state_id=state_id,
        )
    finally:
        try:
            lock.release()
        except Exception:
            pass


def _run_locked(
    agent,
    payload,
    scenario_id,
    view,
    view_id,
    table_id,
    base_id,
    mode,
    phones,
    include_customer_phone,
    dry_run,
    max_records,
    state_id,
):
    table = _resolve_table(agent, base_id, table_id, view)
    view_key = view or view_id

    try:
        # Prefer Cairo-local string values from Airtable when supported by the client.
        try:
            records = table.all(
                view=view_key,
                max_records=max_records,
                time_zone="Africa/Cairo",
                user_locale="en-GB",
                cell_format="string",
            )
        except TypeError:
            records = table.all(view=view_key, max_records=max_records)
        except Exception:
            records = table.all(view=view_key, max_records=max_records)
    except Exception as e:
        if view and view_id and view != view_id:
            try:
                try:
                    records = table.all(
                        view=view_id,
                        max_records=max_records,
                        time_zone="Africa/Cairo",
                        user_locale="en-GB",
                        cell_format="string",
                    )
                except TypeError:
                    records = table.all(view=view_id, max_records=max_records)
            except Exception as e2:
                return {"ok": False, "error": f"airtable_view_failed:{e2}", "sent": False}
        else:
            return {"ok": False, "error": f"airtable_view_failed:{e}", "sent": False}

    seen = _load_seen(agent, state_id)
    seen_set = set(seen)
    notified = 0
    skipped_seen = 0
    skipped_filter = 0
    skipped_dedup = 0
    errors = []
    details = []

    for rec in records or []:
        rid = str((rec or {}).get("id") or "").strip()
        if not rid:
            continue
        if rid in seen_set:
            skipped_seen += 1
            continue
        fields = (rec or {}).get("fields") or {}
        booking_nr = str(_field(fields, "Booking Nr.", "Booking Nr") or "").strip()
        status = _field(fields, "Booking Status")
        canceled = _is_canceled(status)

        alert_kind = None
        if mode in {"both", "cancel+last-minute", "cancel_last_minute"}:
            alert_kind = "cancel" if canceled else "last_minute"
        elif mode in {"cancel", "cancelled"}:
            alert_kind = "cancel"
        else:
            if canceled:
                skipped_filter += 1
                seen.append(rid)
                seen_set.add(rid)
                continue
            alert_kind = "last_minute"

        if alert_kind == "cancel":
            text = _build_cancel(fields, include_customer_phone, agent=agent)
        else:
            text = _build_last_minute(fields, include_customer_phone, agent=agent)

        send_ok_any = False
        phone_results = []
        for phone in phones:
            # Claim BEFORE send — prevents concurrent / overlapping-view duplicates
            if not dry_run:
                claimed = _claim_send(rid, booking_nr, phone, alert_kind, scenario_id)
                if not claimed:
                    skipped_dedup += 1
                    phone_results.append({"phone": phone, "ok": False, "skipped": "dedup_already_sent"})
                    continue

            res = _send_whatsapp(agent, phone, text, dry_run)
            phone_results.append(res)
            if res.get("ok"):
                send_ok_any = True
            elif res.get("error"):
                errors.append(str(res.get("error")))

        # Always mark record seen after processing attempt to stop re-scanning loops.
        # Dedup DB already owns the send-once guarantee per phone.
        seen.append(rid)
        seen_set.add(rid)
        if send_ok_any:
            notified += 1
        details.append({
            "record_id": rid,
            "booking": booking_nr,
            "kind": alert_kind,
            "phones": phone_results,
        })
        # Persist seen incrementally so a crash mid-loop still blocks re-send
        if len(details) % 3 == 0:
            _save_seen(agent, state_id, seen)

    _save_seen(agent, state_id, seen)

    return {
        "ok": True,
        "sent": notified > 0,
        "scenario_id": scenario_id,
        "view": view_key,
        "mode": mode,
        "dry_run": dry_run,
        "scanned": len(records or []),
        "notified": notified,
        "skipped_seen": skipped_seen,
        "skipped_filter": skipped_filter,
        "skipped_dedup": skipped_dedup,
        "errors": errors[:10],
        "details": details[:30],
    }
