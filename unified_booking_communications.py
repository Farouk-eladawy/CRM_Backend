import re
import time
from datetime import datetime
from html import unescape as _html_unescape

import email_templates
from airtable_fields import FieldIds, ID_TO_READABLE_NAME


def _clean_phone(value: str) -> str:
    s = str(value or "").strip()
    digits = re.sub(r"[^\d]", "", s)
    return digits


def _is_valid_email(value: str) -> bool:
    s = str(value or "").strip()
    if not s or "@" not in s:
        return False
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", s))


def _infer_location_from_text(text: str) -> str:
    s = str(text or "").lower()
    sharm_keys = [
        "sharm",
        "sharm el",
        "sharm el-sheikh",
        "ras mohamed",
        "dahab",
        "blue hole",
        "naama",
        "nabq",
    ]
    if any(k in s for k in sharm_keys):
        return "Sharm"
    hc_keys = ["hurghada", "cairo", "giza", "luxor", "aswan", "alexandria"]
    if any(k in s for k in hc_keys):
        return "Hurghada/Cairo"
    return "Unknown"


def _infer_location(agent, fields: dict, default_location: str) -> str:
    for key in ("Location", "location"):
        if str(fields.get(key) or "").strip():
            loc = str(fields.get(key) or "").strip()
            if "sharm" in loc.lower():
                return "Sharm"
            return "Hurghada/Cairo" if loc else default_location

    des = str(agent.get_field_value(fields, FieldIds.DES) or "").strip()
    trip_name = str(agent.get_field_value(fields, FieldIds.TRIP_NAME) or "").strip()
    option_val = agent.get_field_value(fields, FieldIds.OPTION)
    option_str = ""
    if isinstance(option_val, list):
        option_str = ", ".join([str(x or "").strip() for x in option_val if str(x or "").strip()])
    else:
        option_str = str(option_val or "").strip()

    combined = "\n".join([des, trip_name, option_str]).strip()
    inferred = _infer_location_from_text(combined)
    if inferred != "Unknown":
        return inferred
    return str(default_location or "Hurghada/Cairo").strip() or "Hurghada/Cairo"


def _extract_attachment_items(agent, fields: dict) -> list[dict]:
    out: list[dict] = []

    def _append(value):
        if not value:
            return
        if isinstance(value, str):
            out.append({"url": value, "filename": "document"})
            return
        if isinstance(value, dict):
            out.append(value)
            return
        if isinstance(value, list):
            for x in value:
                if isinstance(x, dict):
                    out.append(x)
                elif isinstance(x, str) and x.strip():
                    out.append({"url": x, "filename": "document"})

    _append(agent.get_field_value(fields, FieldIds.ATTACHMENTS))
    _append(agent.get_field_value(fields, FieldIds.TICKETS))
    return [x for x in out if str(x.get("url") or "").strip()]


def _is_pdf(att: dict) -> bool:
    fn = str(att.get("filename") or "").lower()
    url = str(att.get("url") or "").split("?", 1)[0].lower()
    mime = str(att.get("type") or "").lower()
    return fn.endswith(".pdf") or url.endswith(".pdf") or mime.startswith("application/pdf")


def _guess_wa_header_type(att: dict) -> str:
    if _is_pdf(att):
        return "document"
    fn = str(att.get("filename") or "").lower()
    url = str(att.get("url") or "").split("?", 1)[0].lower()
    if fn.endswith((".jpg", ".jpeg", ".png", ".webp")) or url.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return "image"
    return "document"


def _pick_template(templates_cfg: dict, key: str, location: str, fallback: str) -> str:
    m = templates_cfg.get(key) if isinstance(templates_cfg, dict) else None
    if isinstance(m, dict):
        loc_val = m.get(location)
        if str(loc_val or "").strip():
            return str(loc_val).strip()
        def_val = m.get("default")
        if str(def_val or "").strip():
            return str(def_val).strip()
    if str(m or "").strip():
        return str(m).strip()
    return str(fallback or "").strip()


def _html_to_preview_text(html: str, limit: int = 800) -> str:
    s = str(html or "")
    if not s:
        return ""
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\\1>", " ", s)
    s = re.sub(r"(?i)<br\\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|div|h\\d|li|tr)>", "\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "- ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    s = _html_unescape(s)
    s = re.sub(r"[ \\t\\f\\v]+", " ", s)
    s = re.sub(r"\\n{3,}", "\n\n", s)
    s = re.sub(r"\\s*\\n\\s*", "\n", s).strip()
    if limit and len(s) > limit:
        return s[:limit].rstrip() + "..."
    return s


def _send_whatsapp_template(
    agent,
    record_id: str,
    location: str,
    receiving_phone_id: str | None,
    phone: str,
    template_name: str,
    template_language: str,
    template_variables,
    header_att: dict | None = None,
    log_label: str | None = None,
):
    header_url = None
    header_type = None
    if header_att:
        header_url = str(header_att.get("url") or "").strip() or None
        header_type = _guess_wa_header_type(header_att) if header_url else None
    ok, meta = agent.send_whatsapp_message(
        phone,
        text="",
        location=location,
        template_name=template_name,
        template_language=template_language,
        template_variables=template_variables,
        receiving_phone_id=receiving_phone_id,
        template_header_media_url=header_url,
        template_header_media_type=header_type,
    )
    if ok:
        try:
            import chat_db

            conv = chat_db.get_or_create_conversation(
                source="WhatsApp",
                sender_identifier=phone,
                contact_name="",
                airtable_record_id=record_id,
                location=location,
                receiving_phone_id=str((meta or {}).get("phone_number_id") or "") if isinstance(meta, dict) else "",
            )
            chat_id = str((conv or {}).get("chat_id") or "").strip()
            if chat_id:
                shown = ""
                try:
                    shown = str((meta or {}).get("template_text") or "").strip() if isinstance(meta, dict) else ""
                except Exception:
                    shown = ""
                label = str(log_label or "").strip() or f"[Sent WhatsApp Template] {template_name}"
                parts = [label]
                if header_url:
                    media_label = "[Sent Image]" if str(header_type or "").lower().strip() == "image" else "[Sent Document]"
                    parts.append(f"{media_label} {header_url}")
                if shown:
                    parts.append(shown)
                text_to_save = "\n".join([p for p in parts if str(p or "").strip()])
                chat_db.add_message(
                    chat_id=chat_id,
                    sender_type="agent",
                    text=text_to_save,
                    status="sent",
                    increment_unread=False,
                    source="WhatsApp",
                    external_message_id=str((meta or {}).get("message_id") or "") if isinstance(meta, dict) else "",
                )
        except Exception:
            pass
    else:
        try:
            import chat_db

            conv = chat_db.get_or_create_conversation(
                source="WhatsApp",
                sender_identifier=phone,
                contact_name="",
                airtable_record_id=record_id,
                location=location,
                receiving_phone_id=receiving_phone_id or "",
            )
            chat_id = str((conv or {}).get("chat_id") or "").strip()
            if chat_id:
                err_txt = ""
                try:
                    if isinstance(meta, dict):
                        sc = meta.get("status_code")
                        body = meta.get("body")
                        if sc:
                            err_txt = f"HTTP {sc}"
                        if body:
                            err_txt = (err_txt + ": " if err_txt else "") + str(body)
                except Exception:
                    err_txt = ""
                label = str(log_label or "").strip() or f"[WhatsApp Failed] {template_name}"
                text_to_save = f"{label}\n{err_txt}".strip() if err_txt else label
                chat_db.add_message(
                    chat_id=chat_id,
                    sender_type="agent",
                    text=text_to_save,
                    status="error",
                    increment_unread=False,
                    source="WhatsApp",
                )
        except Exception:
            pass
    return ok, meta


def _log_email_to_chat(
    record_id: str,
    email: str,
    contact_name: str,
    location: str,
    subject: str,
    log_label: str | None = None,
    body_html: str | None = None,
):
    try:
        import chat_db

        conv = chat_db.get_or_create_conversation(
            source="Email",
            sender_identifier=email,
            contact_name=contact_name or "",
            airtable_record_id=record_id,
            location=location or "Unknown",
        )
        chat_id = str((conv or {}).get("chat_id") or "").strip()
        if chat_id:
            label = str(log_label or "").strip() or f"[Sent Email] {subject}"
            preview = _html_to_preview_text(body_html or "", limit=900) if body_html else ""
            text_to_save = f"{label}\n{preview}".strip() if preview else label
            chat_db.add_message(
                chat_id=chat_id,
                sender_type="agent",
                text=text_to_save,
                status="sent",
                source="Email",
            )
    except Exception:
        pass


def run(agent, payload: dict | None = None) -> dict:
    cfg = payload or {}

    dry_run = bool(cfg.get("dry_run", False))
    send_email = bool(cfg.get("send_email", True))
    send_whatsapp = bool(cfg.get("send_whatsapp", True))
    include_invoice_whatsapp = bool(cfg.get("include_invoice_whatsapp", True))
    template_language = str(cfg.get("template_language") or "en").strip() or "en"

    max_records_default = 50
    try:
        if cfg.get("max_records") is not None:
            max_records_default = int(str(cfg.get("max_records")).strip())
    except Exception:
        max_records_default = 50
    max_records_default = max(1, min(max_records_default, 250))

    views_cfg = cfg.get("views")
    if not isinstance(views_cfg, list) or not views_cfg:
        views_cfg = [
            {"view_name": "30Min Pickup Time", "default_location": "Hurghada/Cairo", "max_records": max_records_default},
            {"view_name": "30Min Pickup Time Sharm", "default_location": "Sharm", "max_records": max_records_default},
            {"view_name": "Auto Send Invoice & Pickup", "default_location": "Hurghada/Cairo", "max_records": max_records_default},
            {"view_name": "QR Send Auto Attachment", "default_location": "Hurghada/Cairo", "max_records": max_records_default},
        ]

    templates_cfg = cfg.get("templates") if isinstance(cfg.get("templates"), dict) else {}

    results = []
    processed_ids: set[str] = set()

    processed = 0
    sent_email_count = 0
    sent_whatsapp_count = 0
    updated_done = 0
    updated_retry = 0
    skipped = 0
    errors = 0

    status_field = ID_TO_READABLE_NAME.get(FieldIds.WHATSAPP_PICKUP_TIME2, "Whatsapp Pickup Time2")

    for vcfg in views_cfg:
        if not isinstance(vcfg, dict):
            continue
        view_name = str(vcfg.get("view_name") or vcfg.get("view") or vcfg.get("name") or "").strip()
        if not view_name:
            continue
        if vcfg.get("enabled") is not None and not bool(vcfg.get("enabled")):
            continue
        default_location = str(vcfg.get("default_location") or "Hurghada/Cairo").strip() or "Hurghada/Cairo"

        max_records = max_records_default
        try:
            if vcfg.get("max_records") is not None:
                max_records = int(str(vcfg.get("max_records")).strip())
        except Exception:
            max_records = max_records_default
        max_records = max(1, min(max_records, 250))

        try:
            records = agent.table.all(view=view_name, max_records=max_records)
        except Exception as e:
            results.append({"view": view_name, "status": "error", "message": str(e)})
            errors += 1
            continue

        for rec in records or []:
            rid = str((rec or {}).get("id") or "").strip()
            if not rid:
                continue
            if rid in processed_ids:
                continue
            processed_ids.add(rid)
            fields = (rec or {}).get("fields") or {}
            processed += 1

            booking_nr = str(agent.get_field_value(fields, FieldIds.BOOKING_NR) or "").strip()
            trip_name = str(agent.get_field_value(fields, FieldIds.TRIP_NAME) or "").strip()
            option_val = agent.get_field_value(fields, FieldIds.OPTION)
            option_str = ""
            if isinstance(option_val, list):
                option_str = ", ".join([str(x or "").strip() for x in option_val if str(x or "").strip()])
            else:
                option_str = str(option_val or "").strip()

            customer_name = str(agent.get_field_value(fields, FieldIds.CUSTOMER_NAME) or "").strip() or "Guest"
            customer_email = (
                str(agent.get_field_value(fields, FieldIds.CUSTOMER_PERSONAL_EMAIL) or "").strip()
                or str(agent.get_field_value(fields, FieldIds.CUSTOMER_EMAIL) or "").strip()
            )
            customer_phone = str(agent.get_field_value(fields, FieldIds.CUSTOMER_PHONE) or "").strip()
            pickup_time = str(agent.get_field_value(fields, FieldIds.PICKUP_TIME) or "").strip()
            hotel_name = str(agent.get_field_value(fields, FieldIds.HOTEL_NAME) or "").strip()
            room_number = str(agent.get_field_value(fields, FieldIds.ROOM_NUMBER) or "").strip()
            agency = str(agent.get_field_value(fields, FieldIds.AGENCY) or "").strip()
            non_billable_addons = str(agent.get_field_value(fields, FieldIds.NON_BILLABLE_ADDONS) or "").strip()
            add_ons = str(agent.get_field_value(fields, FieldIds.ADD_ONS) or agent.get_field_value(fields, FieldIds.COLLECTING_ON_DATE_TRIP) or "").strip()
            add_ons_multi = agent.get_field_value(fields, FieldIds.ADD_ONS_MULTI)
            if isinstance(add_ons_multi, list):
                add_ons_multi = ", ".join([str(x or "").strip() for x in add_ons_multi if str(x or "").strip()])
            else:
                add_ons_multi = str(add_ons_multi or "").strip()
            stripe_invoice = str(agent.get_field_value(fields, FieldIds.STRIPE_INVOICE) or "").strip()
            date_trip_raw = agent.get_field_value(fields, FieldIds.DATE_TRIP)
            _, formatted_trip_date = agent.get_corrected_trip_date(date_trip_raw)
            full_trip_name = trip_name
            if option_str:
                full_trip_name = f"{trip_name} - {option_str}" if trip_name else option_str

            if not booking_nr:
                skipped += 1
                results.append({"record_id": rid, "status": "skipped", "message": "missing_booking_nr", "view": view_name})
                continue

            wa_status = str(fields.get(status_field) or "").strip()
            # #region debug-point A:unified-record-start
            try:
                import json, urllib.request; _p='.dbg/duplicate-pickup-send.env'; _u,_s='http://127.0.0.1:7777/event','duplicate-pickup-send'; exec("try:\n with open(_p, encoding='utf-8') as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({'sessionId':_s,'runId':'pre-fix','hypothesisId':'A','location':'unified_booking_communications.py:395','msg':'[DEBUG] unified record start','data':{'record_id':rid,'view':view_name,'booking_nr':booking_nr,'wa_status':wa_status,'pickup_time':pickup_time,'trip_name':trip_name}}, separators=(',', ':')).encode(), headers={'Content-Type':'application/json'}), timeout=0.25).read()
            except Exception:
                pass
            # #endregion
            if wa_status.lower() == "done":
                skipped += 1
                results.append({"record_id": rid, "status": "skipped", "message": "already_done", "view": view_name, "booking_nr": booking_nr})
                continue

            location = None
            receiving_phone_id = None
            try:
                import chat_db

                existing_conv = chat_db.get_chat_by_record_id(rid)
                if existing_conv:
                    location = str(existing_conv.get("location") or "").strip() or None
                    receiving_phone_id = str(existing_conv.get("receiving_phone_id") or "").strip() or None
            except Exception:
                pass

            if not location:
                location = _infer_location(agent, fields, default_location)

            trip_lower = trip_name.lower()
            option_lower = option_str.lower()
            is_ticket = ("qr" in trip_lower) or ("sound" in trip_lower)
            is_flight = ("plane" in trip_lower) or ("flight" in trip_lower)
            is_audio_guide = "audio guide" in option_lower

            attachments = _extract_attachment_items(agent, fields)

            if dry_run:
                results.append({
                    "record_id": rid,
                    "status": "dry_run",
                    "view": view_name,
                    "booking_nr": booking_nr,
                    "location": location,
                    "trip_name": trip_name,
                    "option": option_str,
                    "has_email": bool(customer_email),
                    "has_phone": bool(customer_phone),
                    "is_ticket": is_ticket,
                    "is_flight": is_flight,
                    "is_audio_guide": is_audio_guide,
                    "attachments": len(attachments),
                    "stripe_invoice": bool(stripe_invoice),
                })
                continue

            email_ok = None
            whatsapp_ok = None
            wa_msgs = 0
            errs_local: list[str] = []

            try:
                if send_email:
                    # #region debug-point B:unified-email-attempt
                    try:
                        import json, urllib.request; _p='.dbg/duplicate-pickup-send.env'; _u,_s='http://127.0.0.1:7777/event','duplicate-pickup-send'; exec("try:\n with open(_p, encoding='utf-8') as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({'sessionId':_s,'runId':'pre-fix','hypothesisId':'B','location':'unified_booking_communications.py:449','msg':'[DEBUG] unified email attempt','data':{'record_id':rid,'booking_nr':booking_nr,'customer_email':customer_email,'is_ticket':is_ticket,'is_flight':is_flight,'pickup_time':pickup_time,'hotel_name':hotel_name}}, separators=(',', ':')).encode(), headers={'Content-Type':'application/json'}), timeout=0.25).read()
                    except Exception:
                        pass
                    # #endregion
                    
                    import chat_db
                    # Deduplication checks
                    if is_ticket:
                        already_sent_email = chat_db.was_message_sent_recently(rid, "[Sent Email] Ticket Email Sent", hours=1)
                    else:
                        already_sent_email = chat_db.was_message_sent_recently(rid, "[Sent Email] Pickup Email Sent", hours=1) or \
                                             chat_db.was_message_sent_recently(rid, "[Sent Email] Missing Info Request Sent", hours=1)
                    
                    if already_sent_email:
                        email_ok = True  # Treat as success so we don't retry endlessly
                    elif not customer_email:
                        email_ok = False
                    elif not _is_valid_email(customer_email):
                        email_ok = False
                    else:
                        if not is_ticket:
                            missing_details = []
                            if not hotel_name:
                                missing_details.append("Hotel Name")
                            if not room_number:
                                missing_details.append("Room Number")
                            if missing_details:
                                html = email_templates.generate_missing_info_email(
                                    customer_name, full_trip_name or trip_name, booking_nr, formatted_trip_date, missing_details
                                )
                                subj = f"Action Required: Missing Information for {trip_name} - {booking_nr}"
                                email_ok = bool(agent.send_email(customer_email, subj, html, record_id=rid))
                                if email_ok:
                                    _log_email_to_chat(rid, customer_email, customer_name, location, subj, "[Sent Email] Missing Info Request Sent", html)
                            else:
                                processed_attachments = agent._get_valid_attachments(fields, pdf_only=is_ticket)
                                booking_data = {
                                    "customerName": customer_name,
                                    "bookingNr": booking_nr,
                                    "dateTrip": formatted_trip_date,
                                    "pickupTime": pickup_time,
                                    "hotelName": hotel_name,
                                    "nonBillableAddons": non_billable_addons,
                                    "addOns": add_ons,
                                    "tripName": full_trip_name or trip_name,
                                    "has_attachments": bool(processed_attachments),
                                    "stripeInvoice": stripe_invoice,
                                    "addOnsMulti": add_ons_multi,
                                }
                                html = email_templates.generate_pickup_email_html(booking_data)
                                subj = f"Pickup Details: {full_trip_name or trip_name} - {booking_nr} 🚐"
                                email_ok = bool(agent.send_email(customer_email, subj, html, attachments=processed_attachments, record_id=rid))
                                if email_ok:
                                    _log_email_to_chat(rid, customer_email, customer_name, location, subj, "[Sent Email] Pickup Email Sent", html)
                                if email_ok and is_flight:
                                    time.sleep(1)
                                    airport_html = email_templates.generate_airport_email_html(customer_name, booking_nr, full_trip_name or trip_name)
                                    airport_subject = f"Important Airport Instructions - {full_trip_name or trip_name} {booking_nr} ✈️"
                                    airport_ok = bool(agent.send_email(customer_email, airport_subject, airport_html, record_id=rid))
                                    if airport_ok:
                                        _log_email_to_chat(rid, customer_email, customer_name, location, airport_subject, "[Sent Email] Airport Instructions Sent", airport_html)
                                if email_ok:
                                    sent_email_count += 1

                        if is_ticket:
                            processed_attachments = agent._get_valid_attachments(fields, pdf_only=True)
                            html = email_templates.generate_ticket_email(
                                customer_name,
                                full_trip_name or trip_name,
                                booking_nr,
                                agency,
                                pickup_time=pickup_time,
                                hotel_name=hotel_name,
                                has_attachments=bool(processed_attachments),
                                trip_name=full_trip_name or trip_name,
                            )
                            subj = f"Your Tickets for {full_trip_name or trip_name} - {booking_nr} ✨"
                            email_ok = bool(agent.send_email(customer_email, subj, html, attachments=processed_attachments, record_id=rid))
                            if email_ok:
                                _log_email_to_chat(rid, customer_email, customer_name, location, subj, "[Sent Email] Ticket Email Sent", html)
                                sent_email_count += 1
            except Exception as e:
                email_ok = False
                errs_local.append(f"email:{str(e)}")

            try:
                if send_whatsapp:
                    phone_digits = _clean_phone(customer_phone)
                    # #region debug-point C:unified-whatsapp-attempt
                    try:
                        import json, urllib.request; _p='.dbg/duplicate-pickup-send.env'; _u,_s='http://127.0.0.1:7777/event','duplicate-pickup-send'; exec("try:\n with open(_p, encoding='utf-8') as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({'sessionId':_s,'runId':'pre-fix','hypothesisId':'C','location':'unified_booking_communications.py:522','msg':'[DEBUG] unified whatsapp attempt','data':{'record_id':rid,'booking_nr':booking_nr,'phone_digits':phone_digits,'location':location,'is_ticket':is_ticket,'is_flight':is_flight,'attachments':len(attachments)}}, separators=(',', ':')).encode(), headers={'Content-Type':'application/json'}), timeout=0.25).read()
                    except Exception:
                        pass
                    # #endregion
                    
                    import chat_db
                    # Deduplication checks for WhatsApp
                    if is_ticket:
                        already_sent_wa = chat_db.was_message_sent_recently(rid, "[Sent WhatsApp] Ticket Template Sent", hours=1)
                    else:
                        already_sent_wa = chat_db.was_message_sent_recently(rid, "[Sent WhatsApp] Pickup Template Sent", hours=1) or \
                                          chat_db.was_message_sent_recently(rid, "[Sent WhatsApp] Flight Pickup Template Sent", hours=1)
                                          
                    if already_sent_wa:
                        whatsapp_ok = True # Treat as success so we don't retry endlessly
                    elif not phone_digits:
                        whatsapp_ok = False
                    else:
                        if stripe_invoice and include_invoice_whatsapp:
                            pay_tmpl = _pick_template(
                                templates_cfg,
                                "payment",
                                location,
                                "ftstravels_confirm_payment",
                            )
                            wa_vars = [
                                customer_name,
                                booking_nr,
                                trip_name or booking_nr,
                                stripe_invoice,
                                trip_name or booking_nr,
                                add_ons or "add ons",
                            ]
                            ok, _ = _send_whatsapp_template(
                                agent,
                                rid,
                                location,
                                receiving_phone_id,
                                phone_digits,
                                pay_tmpl,
                                template_language,
                                wa_vars,
                                None,
                                "[Sent WhatsApp] Payment Template Sent",
                            )
                            if ok:
                                wa_msgs += 1

                        if is_ticket:
                            ticket_tmpl = _pick_template(
                                templates_cfg,
                                "qr_with_pickup" if (pickup_time and hotel_name) else "qr",
                                location,
                                "qr_tickets_with_pickup" if (pickup_time and hotel_name) else "new_qr_ticket",
                            )
                            body_vars = [customer_name, full_trip_name or trip_name or booking_nr]
                            if pickup_time and hotel_name:
                                body_vars = [customer_name, full_trip_name or trip_name or booking_nr, pickup_time, hotel_name]
                            structured_vars = {
                                "body": body_vars,
                                "quick_reply_payload": ["Confirm Tickets"] if not (pickup_time and hotel_name) else ["Chat with Support"],
                            }
                            ticket_atts = [a for a in attachments if _is_pdf(a) or _guess_wa_header_type(a) == "document"]
                            if not ticket_atts:
                                ticket_atts = attachments[:1]
                            whatsapp_ok = True
                            for a in ticket_atts[:5]:
                                ok, _ = _send_whatsapp_template(
                                    agent,
                                    rid,
                                    location,
                                    receiving_phone_id,
                                    phone_digits,
                                    ticket_tmpl,
                                    template_language,
                                    structured_vars,
                                    a,
                                    "[Sent WhatsApp] Ticket Template Sent",
                                )
                                wa_msgs += 1 if ok else 0
                                whatsapp_ok = whatsapp_ok and ok

                        else:
                            pickup_tmpl = _pick_template(
                                templates_cfg,
                                "flight" if is_flight else "pickup",
                                location,
                                "attachment_pickup" if is_flight else ("pickup_time_new1" if location == "Sharm" else "whatsapp_pickup_time"),
                            )
                            body_vars = [
                                customer_name,
                                full_trip_name or trip_name or booking_nr,
                                booking_nr,
                                formatted_trip_date,
                                pickup_time or "-",
                                hotel_name or "-",
                            ]
                            structured_vars = {"body": body_vars, "quick_reply_payload": ["Confirm Pickup"]}

                            header_att = attachments[0] if attachments else None
                            ok, _ = _send_whatsapp_template(
                                agent,
                                rid,
                                location,
                                receiving_phone_id,
                                phone_digits,
                                pickup_tmpl,
                                template_language,
                                structured_vars,
                                header_att if is_flight else None,
                                "[Sent WhatsApp] Flight Pickup Template Sent" if is_flight else "[Sent WhatsApp] Pickup Template Sent",
                            )
                            whatsapp_ok = ok
                            wa_msgs += 1 if ok else 0

                            if is_flight:
                                extra_tmpl = _pick_template(templates_cfg, "extra_ticket", location, "fts_ticket")
                                extra_structured = {"quick_reply_payload": ["Confirm Received Ticket"]}
                                extra_atts = attachments[1:] if attachments else []
                                for a in (extra_atts or [])[:4]:
                                    ok2, _ = _send_whatsapp_template(
                                        agent,
                                        rid,
                                        location,
                                        receiving_phone_id,
                                        phone_digits,
                                        extra_tmpl,
                                        template_language,
                                        extra_structured,
                                        a,
                                        "[Sent WhatsApp] Attachment Template Sent",
                                    )
                                    wa_msgs += 1 if ok2 else 0
                                    whatsapp_ok = whatsapp_ok and ok2

                        if is_audio_guide:
                            audio_tmpl = _pick_template(templates_cfg, "audio_guide", location, "audio_guide_app")
                            audio_vars = [customer_name, booking_nr, booking_nr]
                            ok, _ = _send_whatsapp_template(
                                agent,
                                rid,
                                location,
                                receiving_phone_id,
                                phone_digits,
                                audio_tmpl,
                                template_language,
                                audio_vars,
                                None,
                                "[Sent WhatsApp] Audio Guide Template Sent",
                            )
                            wa_msgs += 1 if ok else 0
                            whatsapp_ok = (whatsapp_ok if whatsapp_ok is not None else True) and ok

                        if whatsapp_ok:
                            sent_whatsapp_count += 1
            except Exception as e:
                whatsapp_ok = False
                errs_local.append(f"whatsapp:{str(e)}")

            try:
                should_mark_done = bool(whatsapp_ok) and (not send_email or bool(email_ok) or not customer_email)
                
                # Check for max retries
                if not should_mark_done:
                    import chat_db
                    failed_attempts = chat_db.count_recent_messages(rid, "[WhatsApp Failed]", hours=3)
                    if failed_attempts >= 3:
                        new_status = "Failed - Max Retries"
                        # Create an alert for admin
                        try:
                            conv = chat_db.get_or_create_conversation(
                                source="System",
                                sender_identifier="System",
                                contact_name="System",
                                airtable_record_id=rid,
                                location=location
                            )
                            if conv and conv.get('chat_id'):
                                chat_db.add_message(
                                    chat_id=conv['chat_id'],
                                    sender_type="system",
                                    text=f"⚠️ System Alert: Automation failed 3 times for booking {booking_nr}. Stopped retrying.",
                                    status="error"
                                )
                        except Exception:
                            pass
                    else:
                        new_status = "Try Again"
                else:
                    new_status = "Done"
                    
                # #region debug-point D:unified-status-update
                try:
                    import json, urllib.request; _p='.dbg/duplicate-pickup-send.env'; _u,_s='http://127.0.0.1:7777/event','duplicate-pickup-send'; exec("try:\n with open(_p, encoding='utf-8') as f: c=f.read(); _u=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SERVER_URL=')),_u); _s=next((l.split('=',1)[1] for l in c.split('\\n') if l.startswith('DEBUG_SESSION_ID=')),_s)\nexcept: pass"); urllib.request.urlopen(urllib.request.Request(_u, data=json.dumps({'sessionId':_s,'runId':'pre-fix','hypothesisId':'D','location':'unified_booking_communications.py:668','msg':'[DEBUG] unified status update','data':{'record_id':rid,'booking_nr':booking_nr,'email_ok':email_ok,'whatsapp_ok':whatsapp_ok,'new_status':new_status,'status_field':status_field}}, separators=(',', ':')).encode(), headers={'Content-Type':'application/json'}), timeout=0.25).read()
                except Exception:
                    pass
                # #endregion
                agent.table.update(rid, {status_field: new_status})
                if should_mark_done:
                    updated_done += 1
                else:
                    updated_retry += 1
            except Exception as e:
                errs_local.append(f"airtable_update:{str(e)}")

            processed_result = {
                "record_id": rid,
                "status": "success" if (whatsapp_ok and (email_ok is not False)) else "partial",
                "view": view_name,
                "booking_nr": booking_nr,
                "location": location,
                "trip_name": trip_name,
                "option": option_str,
                "email_ok": email_ok,
                "whatsapp_ok": whatsapp_ok,
                "whatsapp_messages": wa_msgs,
                "updated_status_field": status_field,
                "errors": errs_local,
            }
            results.append(processed_result)
            if errs_local:
                errors += 1

    return {
        "status": "success",
        "data": {
            "processed": processed,
            "sent_email": sent_email_count,
            "sent_whatsapp": sent_whatsapp_count,
            "updated_done": updated_done,
            "updated_retry": updated_retry,
            "skipped": skipped,
            "errors": errors,
            "results": results,
        },
    }
