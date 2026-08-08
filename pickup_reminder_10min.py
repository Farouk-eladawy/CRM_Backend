import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from airtable_fields import FieldIds


def _parse_iso_datetime(value: str) -> datetime:
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw)


def _parse_hhmm(value: str) -> Tuple[int, int]:
    raw = str(value or "").strip()
    parts = raw.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid HH:MM time: {value!r}")
    return int(parts[0]), int(parts[1])


def _tz_from_name(tz_name: str):
    from zoneinfo import ZoneInfo

    try:
        return ZoneInfo(tz_name)
    except Exception:
        if str(tz_name or "").strip().lower() in {"africa/cairo", "cairo"}:
            return ZoneInfo("Egypt")
        raise


def _clean_str(value: Any) -> str:
    return str(value or "").strip()


def _row_value(row: Any, key: str) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[key]
    except Exception:
        return getattr(row, key, None)


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
    # Backward-compatible fallbacks for payloads coming from old script/webhook.
    for key in ("Customer personal email", "Customer Email", "Customer Email "):
        val = _clean_str(fields.get(key))
        if val and "@" in val:
            return val
    return ""


def _clean_phone(value: Any) -> str:
    return re.sub(r"\D", "", _clean_str(value))


def _build_pickup_datetime_cairo(date_trip_value: str, pickup_time_value: str, tz) -> datetime:
    trip_dt = _parse_iso_datetime(date_trip_value)
    if trip_dt.tzinfo is None:
        trip_dt = trip_dt.replace(tzinfo=timezone.utc)
    trip_dt_cairo = trip_dt.astimezone(tz)
    hh, mm = _parse_hhmm(pickup_time_value)
    return datetime.combine(trip_dt_cairo.date(), datetime.min.time(), tzinfo=tz).replace(
        hour=hh, minute=mm, second=0, microsecond=0
    )


def _should_send(now_cairo: datetime, send_time_cairo: datetime, window_seconds: int) -> bool:
    delta = (now_cairo - send_time_cairo).total_seconds()
    return 0 <= delta < window_seconds


def _infer_location(fields: Dict[str, Any], default_location: str = "Hurghada/Cairo") -> str:
    des = _clean_str(fields.get("des") or fields.get("Des") or fields.get("DES"))
    trip_name = _clean_str(fields.get("trip Name") or fields.get("Trip Name"))
    option_name = _clean_str(fields.get("Option") or fields.get("Selected Option"))
    haystack = " | ".join([des, trip_name, option_name]).lower()
    if "sharm" in haystack:
        return "Sharm"
    if "cairo" in haystack or "hurghada" in haystack or "luxor" in haystack:
        return "Hurghada/Cairo"
    return _clean_str(default_location) or "Hurghada/Cairo"


def _ensure_chat(agent, record_id: str, customer_name_short: str, customer_email: str, to_phone: str, location: str, booking_nr: str):
    chat_id = None
    receiving_phone_id = None
    try:
        import chat_db

        existing_conv = chat_db.get_chat_by_record_id(record_id)
        if existing_conv:
            chat_id = _clean_str(_row_value(existing_conv, "chat_id")) or None
            receiving_phone_id = _clean_str(_row_value(existing_conv, "receiving_phone_id")) or None
        if not chat_id:
            # Prefer the customer's WhatsApp conversation when a phone number exists,
            # so reminder timeline entries appear in the main dashboard chat.
            if _clean_str(to_phone):
                identifier = to_phone
                source = "WhatsApp"
            elif _clean_str(customer_email):
                identifier = customer_email
                source = "Email"
            else:
                identifier = booking_nr or record_id
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
    except Exception:
        return None, None
    return chat_id, receiving_phone_id


def _log_email(agent, record_id: str, customer_name_short: str, customer_email: str, to_phone: str, location: str, booking_nr: str, preview_text: str, email_ok: bool):
    try:
        import chat_db

        chat_id, _ = _ensure_chat(agent, record_id, customer_name_short, customer_email, to_phone, location, booking_nr)
        if not chat_id:
            return
        chat_db.add_message(
            chat_id=chat_id,
            sender_type="agent",
            text=f"[Sent Email] Pickup Reminder Email Sent\n{preview_text}",
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
        txt = f"[Sent WhatsApp] Pickup Reminder Template Sent\n{template_text or fallback_text}"
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


def _render_email_html(customer_name: str, booking_nr: str, pickup_time: str, lead_minutes: int) -> str:
    safe_name = html.escape(customer_name or "Guest")
    safe_booking = html.escape(booking_nr or "-")
    safe_pickup = html.escape(pickup_time or "-")
    lead_text = str(max(1, int(lead_minutes)))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Pickup Reminder</title>
</head>
<body style="font-family: Arial, sans-serif; background-color: #ECEFF1; padding: 30px;">
  <div style="max-width: 600px; margin: auto; background-color: #FFFFFF; border-radius: 10px; overflow: hidden; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);">
    <div style="background-color: #FF5722; padding: 20px; text-align: center;">
      <img src="https://ftstravels.com/cropped-logo-2.png" alt="FTS Travels Logo" style="max-height: 80px; margin-bottom: 10px;">
      <h1 style="color: white; margin: 0;">FTS Travels</h1>
      <p style="color: #FFE0B2;">Pickup Reminder</p>
    </div>
    <div style="padding: 25px;">
      <p>Hello <b>{safe_name}</b>,</p>
      <p>
        This is a gentle reminder to please be ready at the scheduled pickup time:
        <b style="color:#FF5722;">{safe_pickup}</b>.
      </p>
      <p style="margin-top: 10px; color: #555;">
        Your pickup time is approximately within the next <b>{lead_text} minutes</b>.
      </p>
      <div style="background-color: #FFF3E0; padding: 15px; border-left: 5px solid #FF9800; margin-top: 20px; border-radius: 5px;">
        <p style="margin: 0; font-size: 15px; color: #333;">
          ⏳ The driver can wait a maximum of <b>5 minutes</b>.
        </p>
      </div>
      <p style="margin-top: 25px;">
        Thank you for your cooperation. ☺️
      </p>
      <div style="text-align: center; margin: 30px 0;">
        <a href="mailto:booking@ftstravels.com?subject=I%27m%20Ready%20-%20Booking%20{safe_booking}"
           style="background-color: #4CAF50; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-size: 18px; display: inline-block;">
          I'm Ready
        </a>
      </div>
      <p style="margin-top: 40px;"><b>Best Regards,</b><br>FTS Operations Team</p>
      <p style="font-size:12px; color:#888; margin-top: 30px; text-align: center;">
        12h/4 Shawky Abdelmenim St., Maadi, Cairo <br>
        +2 01030774440 | booking@ftstravels.com
      </p>
    </div>
  </div>
</body>
</html>"""


def _build_fallback_whatsapp_text(customer_name_short: str, pickup_time: str) -> str:
    return (
        f"*Hello {customer_name_short or 'Guest'}*,\n"
        f"This is a gentle reminder to please be ready at the scheduled pickup time: (*{pickup_time or '-'}*). "
        "The driver can wait a maximum of 5 minutes.\n"
        "Thank you for your cooperation. ☺️"
    )


def _normalize_booking_fields(fields: Dict[str, Any], agent) -> Dict[str, Any]:
    booking_nr = _clean_str(agent.get_field_value(fields, FieldIds.BOOKING_NR) or fields.get("Booking Nr."))
    customer_name = _clean_str(agent.get_field_value(fields, FieldIds.CUSTOMER_NAME) or fields.get("Customer Name"))
    trip_name = _clean_str(agent.get_field_value(fields, FieldIds.TRIP_NAME) or fields.get("trip Name") or fields.get("Trip Name"))
    pickup_time = _clean_str(agent.get_field_value(fields, FieldIds.PICKUP_TIME) or fields.get("pickup time") or fields.get("Pickup Time"))
    hotel_name = _clean_str(agent.get_field_value(fields, FieldIds.HOTEL_NAME) or fields.get("Hotel Name"))
    customer_phone = _clean_str(agent.get_field_value(fields, FieldIds.CUSTOMER_PHONE) or fields.get("Customer Phone"))
    customer_email = _select_email(fields, agent)
    date_trip = _clean_str(agent.get_field_value(fields, FieldIds.DATE_TRIP) or fields.get("Date Trip"))
    last_sent = _clean_str(agent.get_field_value(fields, FieldIds.LAST_SENT) or fields.get("Last Sent"))
    des = _clean_str(agent.get_field_value(fields, FieldIds.DES) or fields.get("des"))
    option_name = agent.get_field_value(fields, FieldIds.OPTION) or fields.get("Option")
    if isinstance(option_name, list):
        option_name = ", ".join(_clean_str(x) for x in option_name if _clean_str(x))
    option_name = _clean_str(option_name)
    return {
        "Booking Nr.": booking_nr,
        "Customer Name": customer_name,
        "Customer Email": customer_email,
        "Customer Phone": customer_phone,
        "trip Name": trip_name,
        "pickup time": pickup_time,
        "Date Trip": date_trip,
        "Last Sent": last_sent,
        "Hotel Name": hotel_name,
        "des": des,
        "Option": option_name,
    }


def run(agent, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = payload or {}

    view = _clean_str(payload.get("view")) or "Reminder 10min"
    record_ids = payload.get("record_ids")
    max_records = int(payload.get("max_records") or 250)
    dry_run = bool(payload.get("dry_run", False))
    notify_whatsapp = bool(payload.get("notify_whatsapp", True))
    notify_email = bool(payload.get("notify_email", True))
    lead_minutes = int(payload.get("lead_minutes") or 30)
    window_seconds = int(payload.get("window_seconds") or payload.get("poll_seconds") or 60)
    tz_name = _clean_str(payload.get("timezone")) or "Africa/Cairo"
    whatsapp_template_name = _clean_str(payload.get("whatsapp_template_name")) or "our_wayss"
    whatsapp_template_language = _clean_str(payload.get("whatsapp_template_language")) or "en"
    quick_reply_payloads = payload.get("quick_reply_payloads")
    if not isinstance(quick_reply_payloads, list) or not quick_reply_payloads:
        quick_reply_payloads = ["I'm Ready"]
    status_field = _clean_str(payload.get("status_field")) or "Send Reminder Pickup"
    done_value = _clean_str(payload.get("done_value")) or "Done"
    retry_value = _clean_str(payload.get("retry_value")) or "Try Again"
    last_sent_field = _clean_str(payload.get("last_sent_field")) or "Last Sent"
    follow_sales_field = _clean_str(payload.get("follow_sales_field")) or "Follow sales"
    clear_follow_sales = bool(payload.get("clear_follow_sales", True))
    default_location = _clean_str(payload.get("default_location")) or "Hurghada/Cairo"

    tz = _tz_from_name(tz_name)
    now_cairo = datetime.now(tz)
    now_utc = datetime.now(timezone.utc)

    records: List[Dict[str, Any]] = []
    single_record_payload = False

    if payload.get("record_id") and isinstance(payload.get("fields"), dict):
        single_record_payload = True
        records = [{"id": payload.get("record_id"), "fields": payload.get("fields") or {}}]
    elif isinstance(record_ids, list) and record_ids:
        for rid in record_ids[:max_records]:
            rid_s = _clean_str(rid)
            if not rid_s:
                continue
            try:
                records.append(agent.table.get(rid_s))
            except Exception:
                records.append({"id": rid_s, "fields": {}})
    else:
        try:
            import requests as _req
            # Add timeout to Airtable fetch to prevent hanging
            records = agent.table.all(view=view, max_records=max_records)
        except Exception as e:
            return {
                "status": "error",
                "data": {
                    "message": f"Failed to fetch records from Airtable view '{view}': {str(e)}",
                    "requested_view": view,
                },
            }

    results: List[Dict[str, Any]] = []
    success_count = 0
    skipped_count = 0
    error_count = 0
    sent_whatsapp = 0
    sent_email = 0
    updated_done = 0
    updated_retry = 0
    updated_last_sent = 0

    for rec in records or []:
        rid = _clean_str((rec or {}).get("id"))
        raw_fields = (rec or {}).get("fields", {}) or {}
        fields = _normalize_booking_fields(raw_fields, agent)

        booking_nr = _clean_str(fields.get("Booking Nr."))
        customer_name = _clean_str(fields.get("Customer Name")) or "Guest"
        customer_name_short = _short_name(customer_name)
        customer_email = _clean_str(fields.get("Customer Email"))
        customer_phone = _clean_phone(fields.get("Customer Phone"))
        trip_name = _clean_str(fields.get("trip Name"))
        pickup_time = _clean_str(fields.get("pickup time"))
        date_trip = _clean_str(fields.get("Date Trip"))
        last_sent_value = _clean_str(fields.get("Last Sent"))
        hotel_name = _clean_str(fields.get("Hotel Name"))
        location = _infer_location(fields, default_location=default_location)

        if not rid:
            continue
        if not booking_nr:
            skipped_count += 1
            results.append({"record_id": rid, "status": "skipped", "message": "missing Booking Nr."})
            continue
        if not date_trip or not pickup_time:
            skipped_count += 1
            results.append({"record_id": rid, "status": "skipped", "booking_nr": booking_nr, "message": "missing Date Trip or pickup time"})
            continue

        try:
            pickup_dt_cairo = _build_pickup_datetime_cairo(date_trip, pickup_time, tz)
        except Exception:
            skipped_count += 1
            results.append({"record_id": rid, "status": "skipped", "booking_nr": booking_nr, "message": "invalid Date Trip or pickup time"})
            continue

        send_time_cairo = pickup_dt_cairo - timedelta(minutes=lead_minutes)
        if pickup_dt_cairo < now_cairo - timedelta(hours=2):
            skipped_count += 1
            results.append({"record_id": rid, "status": "skipped", "booking_nr": booking_nr, "message": "pickup_already_passed"})
            continue

        if last_sent_value:
            try:
                last_sent = _parse_iso_datetime(last_sent_value)
                if last_sent.tzinfo is None:
                    last_sent = last_sent.replace(tzinfo=timezone.utc)
                last_sent_cairo = last_sent.astimezone(tz)
                if last_sent_cairo >= send_time_cairo - timedelta(minutes=1):
                    skipped_count += 1
                    results.append({"record_id": rid, "status": "skipped", "booking_nr": booking_nr, "message": "already_sent_recently"})
                    continue
            except Exception:
                pass

        if not single_record_payload and not _should_send(now_cairo, send_time_cairo, window_seconds=window_seconds):
            skipped_count += 1
            results.append({
                "record_id": rid,
                "status": "skipped",
                "booking_nr": booking_nr,
                "message": "outside_send_window",
                "send_time_cairo": send_time_cairo.isoformat(),
            })
            continue

        email_subject = f'FTS Travels Reminder For Pickup "{booking_nr}"'
        email_html = _render_email_html(customer_name, booking_nr, pickup_time, lead_minutes)
        email_preview = (
            f"Booking Number: {booking_nr}\n"
            f"Pickup Time: {pickup_time}\n"
            f"Trip: {trip_name or '-'}\n"
            f"Location: {hotel_name or '-'}"
        )
        fallback_whatsapp_text = _build_fallback_whatsapp_text(customer_name_short, pickup_time)

        if dry_run:
            results.append({
                "record_id": rid,
                "status": "dry_run",
                "booking_nr": booking_nr,
                "location": location,
                "send_time_cairo": send_time_cairo.isoformat(),
                "has_email": bool(customer_email),
                "has_phone": bool(customer_phone),
                "template_name": whatsapp_template_name,
                "email_subject": email_subject,
            })
            continue

        email_ok = None
        wa_ok = None
        wa_meta = None
        errs: List[str] = []
        notify_meta: Dict[str, Any] = {}

        if notify_email:
            if customer_email:
                email_ok = bool(agent.send_email(customer_email, email_subject, email_html, record_id=rid))
                notify_meta["email"] = {"ok": email_ok, "to": customer_email}
                if email_ok:
                    sent_email += 1
                else:
                    errs.append("email_send_failed")
                _log_email(agent, rid, customer_name_short, customer_email, customer_phone, location, booking_nr, email_preview, bool(email_ok))
            else:
                email_ok = False
                errs.append("missing_email")

        if notify_whatsapp:
            if customer_phone:
                structured_vars = {
                    "body": [customer_name_short or "Guest", pickup_time or "-"],
                    "quick_reply_payload": [str(x) for x in quick_reply_payloads],
                }
                wa_ok, wa_meta = agent.send_whatsapp_message(
                    customer_phone,
                    text="",
                    location=location or "Unknown",
                    template_name=whatsapp_template_name,
                    template_language=whatsapp_template_language,
                    booking_data=fields,
                    template_variables=structured_vars,
                )
                notify_meta["whatsapp"] = {"ok": bool(wa_ok), "to": customer_phone, "template": whatsapp_template_name}
                if isinstance(wa_meta, dict):
                    notify_meta["whatsapp"]["meta"] = {
                        "status_code": wa_meta.get("status_code"),
                        "phone_number_id": wa_meta.get("phone_number_id"),
                        "message_id": wa_meta.get("message_id"),
                    }
                if wa_ok:
                    sent_whatsapp += 1
                else:
                    errs.append("whatsapp_send_failed")
                _log_whatsapp(agent, rid, customer_name_short, customer_email, customer_phone, location, booking_nr, whatsapp_template_name, bool(wa_ok), wa_meta if isinstance(wa_meta, dict) else None, fallback_whatsapp_text)
            else:
                wa_ok = False
                errs.append("missing_phone")

        try:
            st = done_value
            if notify_whatsapp and wa_ok is False:
                st = retry_value
            elif notify_email and email_ok is False and (not notify_whatsapp or wa_ok):
                st = retry_value
            upd: Dict[str, Any] = {status_field: st}
            if clear_follow_sales and follow_sales_field:
                upd[follow_sales_field] = None
            if (notify_email and email_ok) or (notify_whatsapp and wa_ok):
                upd[last_sent_field] = now_utc.isoformat()
            agent.table.update(rid, upd)
            if st == done_value:
                updated_done += 1
            else:
                updated_retry += 1
            if last_sent_field in upd:
                updated_last_sent += 1
        except Exception as e:
            errs.append(f"airtable_update_failed:{e}")

        if (notify_whatsapp and wa_ok is False) or (notify_email and email_ok is False and not (notify_whatsapp and wa_ok)):
            error_count += 1
            results.append({"record_id": rid, "status": "error", "booking_nr": booking_nr, "notify": notify_meta or None, "errors": errs or None})
            continue

        success_count += 1
        results.append({"record_id": rid, "status": "success", "booking_nr": booking_nr, "notify": notify_meta or None, "errors": errs or None})

    return {
        "status": "success",
        "data": {
            "requested_view": view if not single_record_payload else None,
            "processed": len(results),
            "success": success_count,
            "skipped": skipped_count,
            "errors": error_count,
            "sent_whatsapp": sent_whatsapp,
            "sent_email": sent_email,
            "updated_done": updated_done,
            "updated_retry": updated_retry,
            "updated_last_sent": updated_last_sent,
            "results": results,
        },
    }
