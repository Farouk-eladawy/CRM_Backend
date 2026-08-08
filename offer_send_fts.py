import re
import logging
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

from airtable_fields import FieldIds


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


def _make_redirect_param(full_url: str) -> str:
    u = _clean_str(full_url)
    if not u:
        return ""
    prefixes = [
        "https://redirect-tour.netlify.app/",
        "http://redirect-tour.netlify.app/",
    ]
    for p in prefixes:
        if u.startswith(p):
            return u[len(p):]
    if u.startswith("redirect-tour.netlify.app/"):
        return u[len("redirect-tour.netlify.app/"):]
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


def _ensure_chat(agent, record_id: str, customer_name_short: str, customer_email: str, to_phone: str, booking_nr: str):
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
                location="Hurghada/Cairo",
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


def _log_whatsapp(agent, record_id: str, customer_name_short: str, customer_email: str, to_phone: str, booking_nr: str, template_name: str, wa_ok: bool, wa_meta: Optional[Dict[str, Any]], fallback_text: str):
    try:
        import chat_db

        chat_id, _ = _ensure_chat(agent, record_id, customer_name_short, customer_email, to_phone, booking_nr)
        if not chat_id:
            return
        message_id = None
        template_text = ""
        if isinstance(wa_meta, dict):
            message_id = wa_meta.get("message_id")
            template_text = _clean_str(wa_meta.get("template_text"))
        txt = f"[Sent WhatsApp] Offer Send FTS Template Sent\n{template_text or fallback_text}"
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

    gift1_name = _clean_str(payload.get("template_gift1")) or "gift1"
    gift2_name = _clean_str(payload.get("template_gift2")) or "gift2"

    gift1_button_0 = _clean_str(payload.get("gift1_button_0")) or "https://redirect-tour.netlify.app/?bookingNr={booking_nr}&tour=cairo&redirect=https://www.getyourguide.com/cairo-l92/hurghada-to-cairo-pyramids-museum-for-first-time-visitors-t1196475/&phone={phone}"
    gift1_button_1 = _clean_str(payload.get("gift1_button_1")) or "https://redirect-tour.netlify.app/?bookingNr={booking_nr}&tour=horseRiding&redirect=https://www.getyourguide.com/hurghada-l403/hurghada-desert-sea-horse-riding-tour-woptional-swimming-t1123075/&phone={phone}"
    gift2_button_0 = _clean_str(payload.get("gift2_button_0")) or "https://redirect-tour.netlify.app/?bookingNr={booking_nr}&tour=Luxor&redirect=https://www.getyourguide.com/luxor-l109/hurghada-luxor-valley-of-the-kings-tutankhamun-tomb-trip-t1191624/&phone={phone}"
    gift2_button_1 = _clean_str(payload.get("gift2_button_1")) or "https://redirect-tour.netlify.app/?bookingNr={booking_nr}&tour=horseRiding&redirect=https://www.getyourguide.com/hurghada-l403/hurghada-desert-sea-horse-riding-tour-woptional-swimming-t1123075/&phone={phone}"

    records = agent.table.all(
        view=view,
        max_records=max_records,
        fields=[
            "Booking Nr.",
            "trip Name",
            "Customer Name",
            "Customer Phone",
            "Offer Send Status",
            "Customer Email",
            "Customer personal email",
            "Follow sales",
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
        customer_name = _clean_str(agent.get_field_value(fields, FieldIds.CUSTOMER_NAME) or fields.get("Customer Name")) or "Guest"
        customer_phone = _clean_phone(agent.get_field_value(fields, FieldIds.CUSTOMER_PHONE) or fields.get("Customer Phone"))
        customer_email = _select_email(fields, agent)

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

        t = trip_name.lower()
        template_name = None
        if "luxor" in t:
            template_name = gift1_name
        elif "cairo" in t:
            template_name = gift2_name
        else:
            results.append({"record_id": rid, "status": "skipped", "booking_nr": booking_nr, "message": "no_matching_route"})
            continue

        if not customer_phone:
            results.append({"record_id": rid, "status": "error", "booking_nr": booking_nr, "message": "missing_phone"})
            continue

        if template_name == gift1_name:
            btn0_full = gift1_button_0.format(booking_nr=booking_nr, phone=customer_phone)
            btn1_full = gift1_button_1.format(booking_nr=booking_nr, phone=customer_phone)
        else:
            btn0_full = gift2_button_0.format(booking_nr=booking_nr, phone=customer_phone)
            btn1_full = gift2_button_1.format(booking_nr=booking_nr, phone=customer_phone)

        button_url_params = [_make_redirect_param(btn0_full), _make_redirect_param(btn1_full)]
        structured_vars = {"body": [_short_name(customer_name)], "button_url": button_url_params}
        fallback_text = "\n".join(
            [
                f"Hello {_short_name(customer_name)}",
                f"Booking Number: {booking_nr or '-'}",
                f"Trip: {trip_name or '-'}",
                btn0_full,
                btn1_full,
            ]
        )

        if dry_run:
            results.append(
                {
                    "record_id": rid,
                    "status": "dry_run",
                    "booking_nr": booking_nr,
                    "template_name": template_name,
                    "button_params": button_url_params,
                }
            )
            continue

        wa_ok, wa_meta = agent.send_whatsapp_message(
            customer_phone,
            text="",
            location="Hurghada/Cairo",
            template_name=template_name,
            template_language=template_language,
            booking_data=fields,
            template_variables=structured_vars,
        )
        sent_whatsapp += 1 if wa_ok else 0
        _log_whatsapp(agent, rid, _short_name(customer_name), customer_email, customer_phone, booking_nr, template_name, bool(wa_ok), wa_meta if isinstance(wa_meta, dict) else None, fallback_text)

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
                "template_name": template_name,
                "whatsapp_ok": bool(wa_ok),
                "airtable_status_updated": bool(mark_info.get("status_updated")),
                "follow_sales_cleared": bool(mark_info.get("follow_sales_cleared")),
                "airtable_update_error": mark_info.get("error"),
            }
        )

    return {
        "status": "success",
        "data": {
            "view": view,
            "retry_cooldown_minutes": retry_cooldown_minutes,
            "processed": len(results),
            "sent_whatsapp": sent_whatsapp,
            "updated": updated,
            "results": results,
        },
    }
