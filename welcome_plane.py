import html
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

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


def _infer_location(des: str) -> str:
    if "sharm" in _clean_str(des).lower():
        return "Sharm"
    return "Hurghada/Cairo"


def _ensure_chat(agent, record_id: str, customer_name_short: str, customer_email: str, to_phone: str, location: str, booking_nr: str):
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
                location=location or "Unknown",
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


def _log_email(agent, record_id: str, customer_name_short: str, customer_email: str, to_phone: str, location: str, booking_nr: str, preview_text: str, email_ok: bool):
    try:
        import chat_db

        chat_id, _ = _ensure_chat(agent, record_id, customer_name_short, customer_email, to_phone, location, booking_nr)
        if not chat_id:
            return
        chat_db.add_message(
            chat_id=chat_id,
            sender_type="agent",
            text=f"[Sent Email] Welcome Plane Email Sent\n{preview_text}",
            status="sent" if email_ok else "error",
            increment_unread=False,
            source="Email",
        )
    except Exception:
        pass


def _log_whatsapp(agent, record_id: str, customer_name_short: str, customer_email: str, to_phone: str, location: str, booking_nr: str, template_name: str, wa_ok: bool, wa_meta: Optional[Dict[str, Any]], fallback_text: str):
    try:
        import chat_db

        chat_id, _ = _ensure_chat(agent, record_id, customer_name_short, customer_email, to_phone, location, booking_nr)
        if not chat_id:
            return
        message_id = None
        template_text = ""
        if isinstance(wa_meta, dict):
            message_id = wa_meta.get("message_id")
            template_text = _clean_str(wa_meta.get("template_text"))
        txt = f"[Sent WhatsApp] Welcome Plane Template Sent\n{template_text or fallback_text}"
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


def _render_email_html(customer_name: str, booking_nr: str, option_name: str) -> str:
    safe_name = html.escape(customer_name or "Guest")
    safe_booking = html.escape(booking_nr or "-")
    safe_option = html.escape(option_name or "-")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Trip Details Request</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #ECEFF1; padding: 30px;">
  <div style="max-width: 600px; margin: auto; background-color: #FFFFFF; border-radius: 10px; overflow: hidden; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
    <div style="background-color: #FF5722; padding: 20px; text-align: center;">
      <img src="https://ftstravels.com/cropped-logo-2.png" alt="FTS Travels Logo" style="max-height: 80px; margin-bottom: 10px;">
      <h1 style="color: white; margin: 0;">FTS Travels</h1>
      <p style="color: #FFE0B2;">Booking Details Needed</p>
    </div>
    <div style="padding: 25px;">
      <p>Hello <b>{safe_name}</b>,</p>
      <p>Your booking number is <b>{safe_booking}</b>.</p>
      <p><b>Trip option:</b> {safe_option}</p>
      <p style="margin-top: 18px;">
        Kindly reply with the following details so we can finalize your arrangements:
      </p>
      <ul>
        <li>Names of all travelers</li>
        <li>Ages of children (if any)</li>
        <li>Hotel name</li>
        <li>Room number</li>
      </ul>
      <p style="margin-top: 18px;">Thank you for your cooperation.</p>
      <p style="margin-top: 28px;"><b>Best Regards,</b><br>FTS Operations Team</p>
      <p style="font-size:12px; color:#888; margin-top: 30px; text-align: center;">
        12h/4 Shawky Abdelmenim St., Maadi, Cairo <br>
        +2 01030774440 | booking@ftstravels.com
      </p>
    </div>
  </div>
</body>
</html>"""


def run(agent, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = payload or {}
    view = _clean_str(payload.get("view")) or "Send welcome plane"
    max_records = int(payload.get("max_records") or 10)
    dry_run = bool(payload.get("dry_run", False))
    notify_whatsapp = bool(payload.get("notify_whatsapp", True))
    notify_email = bool(payload.get("notify_email", True))
    done_value = _clean_str(payload.get("done_value")) or "Done"
    retry_value = _clean_str(payload.get("retry_value")) or "Try Again"
    clear_follow_sales = bool(payload.get("clear_follow_sales", True))
    follow_sales_field = _clean_str(payload.get("follow_sales_field")) or "Follow sales"

    results: List[Dict[str, Any]] = []
    sent_whatsapp = 0
    sent_email = 0
    updated_done = 0
    updated_retry = 0

    now_utc = datetime.now(timezone.utc).isoformat()

    records = agent.table.all(view=view, max_records=max_records)

    for rec in records or []:
        rid = _clean_str((rec or {}).get("id"))
        raw_fields = (rec or {}).get("fields", {}) or {}
        if not rid:
            continue

        booking_nr = _clean_str(agent.get_field_value(raw_fields, FieldIds.BOOKING_NR) or raw_fields.get("Booking Nr."))
        customer_name = _clean_str(agent.get_field_value(raw_fields, FieldIds.CUSTOMER_NAME) or raw_fields.get("Customer Name")) or "Guest"
        option_name = agent.get_field_value(raw_fields, FieldIds.OPTION) or raw_fields.get("Option")
        if isinstance(option_name, list):
            option_name = ", ".join(_clean_str(x) for x in option_name if _clean_str(x))
        option_name = _clean_str(option_name)
        des = _clean_str(agent.get_field_value(raw_fields, FieldIds.DES) or raw_fields.get("des"))
        customer_phone = _clean_phone(agent.get_field_value(raw_fields, FieldIds.CUSTOMER_PHONE) or raw_fields.get("Customer Phone"))
        customer_email = _select_email(raw_fields, agent)
        status_val = _clean_str(agent.get_field_value(raw_fields, FieldIds.WHATSAPP_ROOM_SENT) or raw_fields.get("Whatsapp Room & Hotel Sent"))

        if status_val.lower() == done_value.lower():
            results.append({"record_id": rid, "status": "skipped", "booking_nr": booking_nr, "message": "already_done"})
            continue

        location = _infer_location(des)
        template_name = "welcome_plane"
        template_language = "en"
        body_vars = [booking_nr or "-", (option_name + "-") if option_name else "-", customer_name]
        structured_vars = {"body": body_vars, "quick_reply_payload": ["Send Details Now"]}

        email_subject = f"FTS Travels - Booking Details Needed ({booking_nr})"
        email_html = _render_email_html(customer_name, booking_nr, option_name)
        email_preview = f"Booking Number: {booking_nr}\nTrip Option: {option_name or '-'}\nRequested: Travelers / Children ages / Hotel / Room"
        fallback_whatsapp_text = (
            f"Hello {customer_name},\n"
            f"Booking Number: {booking_nr}\n"
            f"Trip Option: {option_name or '-'}\n"
            "Please reply with: traveler names, children ages (if any), hotel name, room number."
        )

        if dry_run:
            results.append({
                "record_id": rid,
                "status": "dry_run",
                "booking_nr": booking_nr,
                "location": location,
                "template_name": template_name,
                "has_email": bool(customer_email),
                "has_phone": bool(customer_phone),
            })
            continue

        email_ok = None
        wa_ok = None
        wa_meta = None

        if notify_email:
            if customer_email:
                email_ok = bool(agent.send_email(customer_email, email_subject, email_html, record_id=rid))
                sent_email += 1 if email_ok else 0
            else:
                email_ok = False
            _log_email(agent, rid, _short_name(customer_name), customer_email, customer_phone, location, booking_nr, email_preview, bool(email_ok))

        if notify_whatsapp:
            if customer_phone:
                wa_ok, wa_meta = agent.send_whatsapp_message(
                    customer_phone,
                    text="",
                    location=location,
                    template_name=template_name,
                    template_language=template_language,
                    booking_data=raw_fields,
                    template_variables=structured_vars,
                )
                sent_whatsapp += 1 if wa_ok else 0
            else:
                wa_ok = False
            _log_whatsapp(agent, rid, _short_name(customer_name), customer_email, customer_phone, location, booking_nr, template_name, bool(wa_ok), wa_meta if isinstance(wa_meta, dict) else None, fallback_whatsapp_text)

        st = done_value
        if (notify_whatsapp and wa_ok is False) and (notify_email and email_ok is False):
            st = retry_value

        try:
            upd: Dict[str, Any] = {FieldIds.WHATSAPP_ROOM_SENT: st}
            if clear_follow_sales and follow_sales_field:
                upd[follow_sales_field] = None
            upd["Last Sent"] = now_utc
            agent.table.update(rid, upd)
            if st == done_value:
                updated_done += 1
            else:
                updated_retry += 1
        except Exception:
            pass

        results.append({
            "record_id": rid,
            "status": "success" if st == done_value else "error",
            "booking_nr": booking_nr,
            "location": location,
            "template_name": template_name,
            "email_ok": bool(email_ok) if email_ok is not None else None,
            "whatsapp_ok": bool(wa_ok) if wa_ok is not None else None,
        })

    return {
        "status": "success",
        "data": {
            "view": view,
            "processed": len(results),
            "sent_email": sent_email,
            "sent_whatsapp": sent_whatsapp,
            "updated_done": updated_done,
            "updated_retry": updated_retry,
            "results": results,
        },
    }

