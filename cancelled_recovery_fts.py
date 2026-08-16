"""
Cancelled Booking Recovery FTS
------------------------------
1) run_send: cancelled eligible booking -> WhatsApp rebook-same-product offer
2) run_bonus: new confirmed booking with same phone + same Product ID as a prior
   Cancelled eligible booking -> create complimentary bonus List record (no Date Trip)

Conservative eligible list (high-value trips only).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

from airtable_fields import FieldIds, ID_TO_READABLE_NAME
from offer_bonus_fts import (
    BONUS_BOOKING_PREFIX,
    BONUS_MARKER,
    _bonus_already_exists,
    _build_bonus_fields,
    _find_records_by_phone,
    _generate_bonus_booking_nr,
    _get_field,
    _mark_second_booking,
    _readable,
    _record_booking_nr,
    _record_phone,
    _record_product_id,
    _remarks_has_bonus_marker,
)
from offer_send_fts import (
    BONUS_HURGHADA_CITY_TOUR,
    BONUS_SHARM_SIGNATURE,
    DEFAULT_OFFER_PRODUCTS,
    REDIRECT_BASE,
    _clean_phone,
    _clean_str,
    _extract_product_id,
    _make_redirect_param,
    _short_name,
    build_offer_redirect_url,
    enrich_product_from_agent,
    get_product_display_name,
)

DEFAULT_RECOVERY_TEMPLATE = "cancel_recovery"
DEFAULT_RECOVERY_TEMPLATE_SHARM = "cancel_recovery_sharm"
DEFAULT_RECOVERY_STATUS_FIELD = "Recovery Offer Status"
RECOVERY_SENT_MARKER = "[RECOVERY_OFFER_SENT]"
RECOVERY_BONUS_NOTE = "Complimentary bonus for cancelled-booking recovery."

# Cancelled Product ID -> bonus Product ID (rebook = SAME product id)
DEFAULT_RECOVERY_ELIGIBLE: Dict[str, Dict[str, str]] = {
    # Hurghada high-value
    "1191624": {"bonus_product_id": BONUS_HURGHADA_CITY_TOUR, "region": "hurghada"},
    "1195745": {"bonus_product_id": BONUS_HURGHADA_CITY_TOUR, "region": "hurghada"},
    "1196475": {"bonus_product_id": BONUS_HURGHADA_CITY_TOUR, "region": "hurghada"},
    "1195743": {"bonus_product_id": BONUS_HURGHADA_CITY_TOUR, "region": "hurghada"},
    "1289272": {"bonus_product_id": BONUS_HURGHADA_CITY_TOUR, "region": "hurghada"},
    "1289286": {"bonus_product_id": BONUS_HURGHADA_CITY_TOUR, "region": "hurghada"},
    "1303745": {"bonus_product_id": BONUS_HURGHADA_CITY_TOUR, "region": "hurghada"},
    # Sharm high-value only
    "1344400": {"bonus_product_id": BONUS_SHARM_SIGNATURE, "region": "sharm"},
    "1273778": {"bonus_product_id": BONUS_SHARM_SIGNATURE, "region": "sharm"},
}


def _is_cancelled_status(value: Any) -> bool:
    s = _clean_str(value).lower()
    if not s:
        return False
    return ("cancel" in s) or ("ملغ" in s) or s in ("cxl", "canceled", "cancelled")


def _is_confirmed_status(value: Any) -> bool:
    s = _clean_str(value).lower()
    if not s:
        # Empty status on a fresh GYG booking is treated as active/confirmed enough
        return True
    if _is_cancelled_status(s):
        return False
    return True


def _booking_status(agent, fields: Dict[str, Any]) -> str:
    return _clean_str(_get_field(agent, fields, FieldIds.BOOKING_STATUS, "Booking Status"))


def _select_email(fields: Dict[str, Any], agent) -> str:
    personal = _clean_str(agent.get_field_value(fields, FieldIds.CUSTOMER_PERSONAL_EMAIL))
    if personal and "@" in personal:
        return personal
    primary = _clean_str(agent.get_field_value(fields, FieldIds.CUSTOMER_EMAIL))
    if primary and "@" in primary:
        return primary
    return ""


def _wa_location(region: str) -> str:
    return "Sharm" if _clean_str(region).lower() == "sharm" else "Hurghada/Cairo"


def _ensure_chat(agent, record_id, customer_name_short, customer_email, to_phone, booking_nr, location="Hurghada/Cairo"):
    try:
        import chat_db

        chat_id = None
        existing = chat_db.get_chat_by_record_id(record_id)
        if existing:
            chat_id = _clean_str(existing.get("chat_id") if isinstance(existing, dict) else existing["chat_id"])
        if not chat_id:
            identifier = _clean_str(to_phone) or _clean_str(customer_email) or _clean_str(booking_nr) or record_id
            source = "WhatsApp" if _clean_str(to_phone) else ("Email" if "@" in _clean_str(customer_email) else "WhatsApp")
            conv = chat_db.get_or_create_conversation(
                source=source,
                sender_identifier=identifier,
                contact_name=customer_name_short or "Guest",
                airtable_record_id=record_id,
                location=location,
                thread_id="",
                receiving_phone_id="",
            )
            chat_id = _clean_str((conv or {}).get("chat_id"))
        if chat_id:
            try:
                chat_db.update_conversation_info(chat_id, booking_number=booking_nr)
            except Exception:
                pass
        return chat_id
    except Exception:
        return None


def _log_whatsapp(agent, record_id, name, email, phone, booking_nr, template_name, wa_ok, wa_meta, fallback, location):
    try:
        import chat_db

        chat_id = _ensure_chat(agent, record_id, name, email, phone, booking_nr, location=location)
        if not chat_id:
            return
        message_id = None
        template_text = ""
        if isinstance(wa_meta, dict):
            message_id = wa_meta.get("message_id")
            template_text = _clean_str(wa_meta.get("template_text"))
        txt = f"[Sent WhatsApp] Cancelled Recovery Offer Sent\n{template_text or fallback}"
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


def _recent_recovery_send(agent, booking_nr: str, within_minutes: int) -> bool:
    booking_nr = _clean_str(booking_nr)
    if not booking_nr or within_minutes <= 0:
        return False
    try:
        import chat_db

        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=int(within_minutes))).isoformat()
        with sqlite3.connect(chat_db.DB_FILE, timeout=15.0) as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT 1
                FROM messages m
                JOIN conversations c ON c.chat_id = m.chat_id
                WHERE c.booking_number = ?
                  AND m.source = 'WhatsApp'
                  AND m.text LIKE ?
                  AND m.timestamp >= ?
                LIMIT 1
                """,
                (booking_nr, "%Cancelled Recovery Offer Sent%", cutoff),
            )
            return bool(c.fetchone())
    except Exception as e:
        logging.warning(f"Recovery cooldown lookup failed: {e}")
        return False


def _truthy_checkbox(value: Any) -> bool:
    if value is True or value == 1:
        return True
    s = str(value or "").strip().lower()
    return s in ("true", "1", "yes", "done", "checked")


def _mark_recovery_sent(agent, record_id: str, dry_run: bool) -> bool:
    """Append Remarks marker only (legacy). Prefer _mark_recovery_processed."""
    if dry_run or not record_id:
        return False
    try:
        rec = agent.table.get(record_id)
        fields = (rec or {}).get("fields") or {}
        remarks_key = _readable(FieldIds.REMARKS, "Remarks")
        old = _clean_str(fields.get(remarks_key) or fields.get("Remarks"))
        if RECOVERY_SENT_MARKER in old:
            return True
        new_remarks = f"{old} | {RECOVERY_SENT_MARKER}".strip(" |") if old else RECOVERY_SENT_MARKER
        agent.update_booking_record(record_id, {remarks_key: new_remarks})
        return True
    except Exception as e:
        logging.warning(f"Failed marking recovery sent on {record_id}: {e}")
        return False


def _mark_recovery_processed(
    agent,
    record_id: str,
    booking_nr: str,
    recovery_status_field: str,
    wa_ok: bool,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Always mark Recovery Offer Status (checkbox) after a send attempt
    (success or failure) so the record leaves the Airtable view and is not re-sent.
    Also keeps the Remarks [RECOVERY_OFFER_SENT] marker for backward compatibility.
    """
    out = {
        "status_updated": False,
        "remarks_updated": False,
        "error": None,
    }
    if dry_run or not record_id:
        return out

    status_field = _clean_str(recovery_status_field) or DEFAULT_RECOVERY_STATUS_FIELD

    try:
        if hasattr(agent, "update_booking_record"):
            agent.update_booking_record(record_id, {status_field: True})
        else:
            agent.table.update(record_id, {status_field: True})
        out["status_updated"] = True
    except Exception as e:
        out["error"] = f"status_update_failed: {e}"
        logging.error(
            "Cancelled Recovery failed to set %s for %s (%s): %s",
            status_field,
            booking_nr or record_id,
            "success" if wa_ok else "error",
            e,
            exc_info=True,
        )

    # Best-effort Remarks marker (do not block if checkbox already saved)
    try:
        out["remarks_updated"] = bool(_mark_recovery_sent(agent, record_id, dry_run=False))
    except Exception as e:
        logging.warning(
            "Recovery status saved but Remarks marker failed for %s: %s",
            booking_nr or record_id,
            e,
        )
        if not out["error"]:
            out["error"] = f"remarks_update_failed: {e}"

    return out


def _fetch_view_or_formula(agent, view: str, formula: str, max_records: int) -> List[Dict[str, Any]]:
    view = _clean_str(view)
    if view:
        try:
            return list(agent.table.all(view=view, max_records=max_records) or [])
        except Exception as e:
            logging.warning(f"Recovery view fetch failed ({view}): {e}")
    if not formula:
        return []
    try:
        return list(agent.table.all(formula=formula, max_records=max_records) or [])
    except Exception as e:
        logging.error(f"Recovery formula fetch failed: {e}", exc_info=True)
        return []


def run_send(agent, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send rebook offer for cancelled eligible bookings."""
    payload = payload or {}
    view = _clean_str(payload.get("view")) or "Cancelled Recovery Offer"
    max_records = int(payload.get("max_records") or 15)
    dry_run = bool(payload.get("dry_run", True))
    template_language = _clean_str(payload.get("template_language")) or "en"
    template_hurghada = _clean_str(payload.get("template_name")) or DEFAULT_RECOVERY_TEMPLATE
    template_sharm = _clean_str(payload.get("template_name_sharm")) or DEFAULT_RECOVERY_TEMPLATE_SHARM
    redirect_base = _clean_str(payload.get("redirect_base")) or REDIRECT_BASE
    cooldown = int(payload.get("retry_cooldown_minutes") or 180)
    recovery_status_field = (
        _clean_str(payload.get("recovery_status_field")) or DEFAULT_RECOVERY_STATUS_FIELD
    )

    eligible = dict(DEFAULT_RECOVERY_ELIGIBLE)
    if isinstance(payload.get("eligible"), dict) and payload.get("eligible"):
        eligible.update(payload["eligible"])

    product_map = DEFAULT_OFFER_PRODUCTS
    if isinstance(payload.get("products"), dict) and payload.get("products"):
        product_map = {**DEFAULT_OFFER_PRODUCTS, **payload["products"]}

    # Fallback formula if view missing: cancelled + any eligible product id
    pid_bits = [f"FIND('{pid}', {{Product ID}}&'')" for pid in sorted(eligible.keys())]
    formula = (
        f"AND("
        f"OR(FIND('Cancel', {{Booking Status}}&''), FIND('cancel', {{Booking Status}}&''), FIND('CANCEL', {{Booking Status}}&'')),"
        f"OR({','.join(pid_bits)})"
        f")"
    ) if pid_bits else ""

    records = _fetch_view_or_formula(agent, view, formula, max_records)
    results: List[Dict[str, Any]] = []
    sent = 0
    updated = 0
    analytics_cache: Dict[str, str] = {}

    for rec in records or []:
        rid = _clean_str((rec or {}).get("id"))
        fields = (rec or {}).get("fields") or {}
        if not rid:
            continue

        pid = _record_product_id(agent, fields)
        phone = _record_phone(agent, fields)
        booking_nr = _record_booking_nr(agent, fields)
        status = _booking_status(agent, fields)
        trip_name = _clean_str(_get_field(agent, fields, FieldIds.TRIP_NAME, "trip Name"))
        customer_name = _clean_str(_get_field(agent, fields, FieldIds.CUSTOMER_NAME, "Customer Name")) or "Guest"
        short_name = _short_name(customer_name)
        remarks = _clean_str(_get_field(agent, fields, FieldIds.REMARKS, "Remarks"))
        already_marked = _truthy_checkbox(
            fields.get(recovery_status_field) or fields.get(DEFAULT_RECOVERY_STATUS_FIELD)
        )

        if pid not in eligible:
            results.append({"record_id": rid, "status": "skipped", "message": "not_eligible_product", "product_id": pid})
            continue
        if not _is_cancelled_status(status):
            results.append({"record_id": rid, "status": "skipped", "message": "not_cancelled", "booking_status": status})
            continue
        if already_marked or RECOVERY_SENT_MARKER in remarks:
            results.append({"record_id": rid, "status": "skipped", "message": "already_sent_marked", "booking_nr": booking_nr})
            continue
        if not phone:
            results.append({"record_id": rid, "status": "error", "message": "missing_phone", "booking_nr": booking_nr})
            continue
        if _recent_recovery_send(agent, booking_nr, cooldown):
            # Previous attempt already happened but Airtable checkbox may never
            # have been marked. Mark it now so the record leaves the view.
            mark_info = {"status_updated": False, "error": None}
            if not dry_run:
                mark_info = _mark_recovery_processed(
                    agent, rid, booking_nr, recovery_status_field, wa_ok=False, dry_run=False
                )
                if mark_info.get("status_updated"):
                    updated += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "message": "recent_attempt_cooldown",
                    "booking_nr": booking_nr,
                    "airtable_status_updated": bool(mark_info.get("status_updated")),
                    "airtable_update_error": mark_info.get("error"),
                }
            )
            continue

        cfg = eligible[pid]
        bonus_pid = _extract_product_id(cfg.get("bonus_product_id"))
        region = _clean_str(cfg.get("region")) or "hurghada"
        product_meta = enrich_product_from_agent(agent, pid, product_map=product_map, analytics_cache=analytics_cache)
        trip_display = trip_name or product_meta.get("display_name") or pid
        bonus_display = get_product_display_name(bonus_pid, product_map, fallback="complimentary tour")

        btn_full = build_offer_redirect_url(
            booking_nr,
            phone,
            pid,
            tour_key=product_meta.get("tour"),
            gyg_url=product_meta.get("url"),
            product_map=product_map,
            redirect_base=redirect_base,
        )
        if not btn_full:
            results.append({"record_id": rid, "status": "error", "message": "failed_build_redirect", "booking_nr": booking_nr})
            continue

        button_params = [_make_redirect_param(btn_full)]
        # Meta template: {{1}} name, {{2}} cancelled trip, {{3}} bonus name (recommended)
        structured_vars = {
            "body": [short_name, trip_display, bonus_display],
            "button_url": button_params,
        }
        template_name = template_sharm if region == "sharm" else template_hurghada
        wa_location = _wa_location(region)
        fallback = "\n".join(
            [
                f"Hi {short_name}",
                f"We noticed that your {trip_display} booking was cancelled.",
                f"Rebook the same experience and receive {bonus_display} complimentary.",
                btn_full,
            ]
        )

        if dry_run:
            results.append(
                {
                    "record_id": rid,
                    "status": "dry_run",
                    "booking_nr": booking_nr,
                    "product_id": pid,
                    "bonus_product_id": bonus_pid,
                    "template_name": template_name,
                    "body_vars": structured_vars["body"],
                    "button_params": button_params,
                    "whatsapp_location": wa_location,
                    "recovery_status_field": recovery_status_field,
                }
            )
            continue

        wa_ok, wa_meta = agent.send_whatsapp_message(
            phone,
            text="",
            location=wa_location,
            template_name=template_name,
            template_language=template_language,
            booking_data=fields,
            template_variables=structured_vars,
        )
        sent += 1 if wa_ok else 0
        _log_whatsapp(
            agent,
            rid,
            short_name,
            _select_email(fields, agent),
            phone,
            booking_nr,
            template_name,
            bool(wa_ok),
            wa_meta if isinstance(wa_meta, dict) else None,
            fallback,
            wa_location,
        )
        # Mark Recovery Offer Status on success OR failure to avoid loops
        mark_info = _mark_recovery_processed(
            agent, rid, booking_nr, recovery_status_field, wa_ok=bool(wa_ok), dry_run=False
        )
        if mark_info.get("status_updated"):
            updated += 1
        results.append(
            {
                "record_id": rid,
                "status": "success" if wa_ok else "error",
                "booking_nr": booking_nr,
                "product_id": pid,
                "template_name": template_name,
                "whatsapp_ok": bool(wa_ok),
                "airtable_status_updated": bool(mark_info.get("status_updated")),
                "airtable_update_error": mark_info.get("error"),
            }
        )

    return {
        "status": "success",
        "data": {
            "mode": "send",
            "view": view,
            "dry_run": dry_run,
            "recovery_status_field": recovery_status_field,
            "eligible_product_ids": sorted(eligible.keys()),
            "processed": len(results),
            "sent_whatsapp": sent,
            "airtable_updated": updated,
            "results": results,
        },
    }


def _find_prior_cancelled_same_product(
    agent,
    phone: str,
    product_id: str,
    exclude_record_id: str,
) -> Optional[Dict[str, Any]]:
    pid = _extract_product_id(product_id)
    for rec in _find_records_by_phone(agent, phone):
        rid = _clean_str((rec or {}).get("id"))
        if not rid or rid == exclude_record_id:
            continue
        fields = (rec or {}).get("fields") or {}
        bn = _record_booking_nr(agent, fields)
        if bn.startswith(BONUS_BOOKING_PREFIX):
            continue
        if _record_product_id(agent, fields) != pid:
            continue
        if _is_cancelled_status(_booking_status(agent, fields)):
            return rec
    return None


def run_bonus(agent, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create bonus record when customer rebooks the SAME product after a Cancelled booking.
    Match: same phone + same Product ID + prior Booking Status cancelled.
    New booking must not be cancelled.
    """
    payload = payload or {}
    view = _clean_str(payload.get("view")) or "Cancelled Recovery Rebook"
    max_records = int(payload.get("max_records") or 25)
    dry_run = bool(payload.get("dry_run", True))

    eligible = dict(DEFAULT_RECOVERY_ELIGIBLE)
    if isinstance(payload.get("eligible"), dict) and payload.get("eligible"):
        eligible.update(payload["eligible"])

    product_map = DEFAULT_OFFER_PRODUCTS
    if isinstance(payload.get("products"), dict) and payload.get("products"):
        product_map = {**DEFAULT_OFFER_PRODUCTS, **payload["products"]}

    pid_bits = [f"FIND('{pid}', {{Product ID}}&'')" for pid in sorted(eligible.keys())]
    formula = f"OR({','.join(pid_bits)})" if pid_bits else ""
    records = _fetch_view_or_formula(agent, view, formula, max_records)

    results: List[Dict[str, Any]] = []
    created = 0
    skipped = 0

    for rec in records or []:
        rid = _clean_str((rec or {}).get("id"))
        fields = (rec or {}).get("fields") or {}
        if not rid:
            continue

        pid = _record_product_id(agent, fields)
        phone = _record_phone(agent, fields)
        booking_nr = _record_booking_nr(agent, fields)
        status = _booking_status(agent, fields)

        if booking_nr.startswith(BONUS_BOOKING_PREFIX):
            skipped += 1
            results.append({"record_id": rid, "status": "skipped", "message": "is_bonus_record"})
            continue
        if pid not in eligible:
            skipped += 1
            results.append({"record_id": rid, "status": "skipped", "message": "not_eligible_product", "product_id": pid})
            continue
        if _is_cancelled_status(status):
            skipped += 1
            results.append({"record_id": rid, "status": "skipped", "message": "new_booking_is_cancelled", "booking_nr": booking_nr})
            continue
        if not _is_confirmed_status(status):
            skipped += 1
            results.append({"record_id": rid, "status": "skipped", "message": "new_booking_not_active", "booking_status": status})
            continue
        if _remarks_has_bonus_marker(_get_field(agent, fields, FieldIds.REMARKS, "Remarks")):
            skipped += 1
            results.append({"record_id": rid, "status": "skipped", "message": "already_marked_bonus_created", "booking_nr": booking_nr})
            continue
        if not phone:
            skipped += 1
            results.append({"record_id": rid, "status": "error", "message": "missing_phone", "booking_nr": booking_nr})
            continue

        prior = _find_prior_cancelled_same_product(agent, phone, pid, exclude_record_id=rid)
        if not prior:
            skipped += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "message": "no_prior_cancelled_same_product",
                    "booking_nr": booking_nr,
                    "product_id": pid,
                    "phone": phone,
                }
            )
            continue

        prior_fields = (prior or {}).get("fields") or {}
        prior_bn = _record_booking_nr(agent, prior_fields)
        bonus_pid = _extract_product_id((eligible[pid] or {}).get("bonus_product_id"))

        if _bonus_already_exists(agent, phone, bonus_pid):
            skipped += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "skipped",
                    "message": "bonus_already_exists",
                    "booking_nr": booking_nr,
                    "first_booking_nr": prior_bn,
                    "bonus_product_id": bonus_pid,
                }
            )
            continue

        bonus_name = get_product_display_name(bonus_pid, product_map, fallback=f"Bonus {bonus_pid}")
        if "free" not in bonus_name.lower():
            bonus_name = f"{bonus_name} FREE"

        bonus_bn = _generate_bonus_booking_nr()
        create_fields = _build_bonus_fields(
            agent,
            prior_fields,
            fields,
            bonus_pid,
            bonus_name,
            bonus_bn,
            prior_bn,
            booking_nr,
        )
        # Clarify remarks for recovery (not cross-sell)
        remarks_key = _readable(FieldIds.REMARKS, "Remarks")
        create_fields[remarks_key] = (
            f"{BONUS_MARKER}{bonus_bn}] {RECOVERY_BONUS_NOTE} "
            f"Cancelled booking: {prior_bn or '-'}. "
            f"Rebooked: {booking_nr or '-'} (same Product ID {pid}). "
            f"Date Trip left empty for operations."
        )
        note_key = _readable(FieldIds.NOTE, "Note")
        create_fields[note_key] = (
            f"{RECOVERY_BONUS_NOTE} Phone match. Cancelled {prior_bn} -> rebook {booking_nr}."
        )

        if dry_run:
            results.append(
                {
                    "record_id": rid,
                    "status": "dry_run",
                    "booking_nr": booking_nr,
                    "phone": phone,
                    "cancelled_booking_nr": prior_bn,
                    "product_id": pid,
                    "bonus_product_id": bonus_pid,
                    "bonus_booking_nr": bonus_bn,
                    "bonus_trip_name": bonus_name,
                    "create_fields": create_fields,
                }
            )
            continue

        try:
            created_rec = agent.table.create(create_fields, typecast=True)
            created_id = _clean_str((created_rec or {}).get("id"))
            _mark_second_booking(agent, rid, bonus_bn, dry_run=False)
            created += 1
            results.append(
                {
                    "record_id": rid,
                    "status": "success",
                    "booking_nr": booking_nr,
                    "phone": phone,
                    "cancelled_booking_nr": prior_bn,
                    "product_id": pid,
                    "bonus_product_id": bonus_pid,
                    "bonus_booking_nr": bonus_bn,
                    "bonus_record_id": created_id,
                    "bonus_trip_name": bonus_name,
                }
            )
        except Exception as e:
            logging.error(f"Recovery bonus create failed for {booking_nr}: {e}", exc_info=True)
            results.append({"record_id": rid, "status": "error", "booking_nr": booking_nr, "message": f"create_failed: {e}"})

    return {
        "status": "success",
        "data": {
            "mode": "bonus",
            "view": view,
            "dry_run": dry_run,
            "eligible_product_ids": sorted(eligible.keys()),
            "processed": len(results),
            "created": created,
            "skipped": skipped,
            "results": results,
        },
    }


def run(agent, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Dispatch: payload.mode = send|bonus (default send)."""
    payload = payload or {}
    mode = _clean_str(payload.get("mode")).lower() or "send"
    if mode in ("bonus", "create_bonus", "recovery_bonus"):
        return run_bonus(agent, payload)
    return run_send(agent, payload)
