"""
Internal Notifications — webhook forwarder (Make.com Custom Webhook replacement).

Handles:
  - aegypten_requests
  - ceo_report
  - daily_report_group

Called via POST /api/internal_notifications/webhook/<slug>
or automation run_script with payload {scenario_id|webhook_slug, ...fields}.
"""

from __future__ import annotations

import json
import logging
import os
import re

from fts_paths import get_data_path

log = logging.getLogger("InternalWebhookNotify")
SCENARIOS_PATH = os.path.join(get_data_path("workflows"), "internal_notification_scenarios.json")


def _load_scenarios():
    try:
        with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return list(data.get("scenarios") or [])
    except Exception:
        return []


def _find_by_slug(slug: str):
    slug = str(slug or "").strip().lower()
    for s in _load_scenarios():
        if str(s.get("webhook_slug") or "").strip().lower() == slug:
            return s
        if str(s.get("id") or "").strip().lower() == slug:
            return s
    return None


def _norm_phone(raw) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    if "@g.us" in s:
        return s
    return re.sub(r"\D", "", s)


def _send(agent, phone: str, text: str, dry_run: bool):
    phone = _norm_phone(phone)
    text = str(text or "").strip()
    if not phone or not text:
        return {"phone": phone, "ok": False, "error": "missing"}
    if dry_run:
        return {"phone": phone, "ok": True, "dry_run": True}
    try:
        ok = bool(agent.send_internal_notifications_whatsapp_text(phone, text))
        return {"phone": phone, "ok": ok}
    except Exception as e:
        return {"phone": phone, "ok": False, "error": str(e)}


def _contains(hay, needle) -> bool:
    return str(needle or "").lower() in str(hay or "").lower()


def _handle_aegypten(agent, data: dict, dry_run: bool):
    results = []
    message = str(data.get("message") or "")
    file_name = str(data.get("fileName") or data.get("file_name") or "")
    source = str(data.get("source") or "")
    name = str(data.get("name") or "")
    phone = str(data.get("phone") or "")
    email = str(data.get("email") or "")
    contact_from = str(data.get("contact_from") or "")
    ai_response = str(data.get("ai_response") or "")
    sender_email = str(data.get("sender_email") or "")
    sender_phone = str(data.get("sender_phone") or "")
    intent = str(data.get("intent") or "")
    chat_id = str(data.get("chat_id") or "")
    sender_name = str(data.get("sender_name") or "")

    # Route 1: Report_Standard (not Backup) -> ops phones
    if (not _contains(message, "Backup")) and _contains(file_name, "Report_Standard"):
        text = (
            "FTS Travels Automation Team \n"
            "📢 New_Requests_Alert! 🚀 \n"
            "📍 Request Details: Ägypten_Requests \n"
            f"name: {name} \n"
            f"phone: {phone} \n"
            f"email: {email} \n"
            f"contact_from: {contact_from} \n"
            f"AI Message Analyses: {message}"
        )
        results.append(_send(agent, "+201061029883", text, dry_run))

    # Route 2: always notify secondary
    text2 = (
        "FTS Travels Automation Team \n"
        "📢 New_Requests_Alert! 🚀 \n"
        "📍 Request Details: Ägypten_Requests \n"
        f"name: {name} \n"
        f"phone: {phone} \n"
        f"email: {email} \n"
        f"contact_from: {contact_from} \n"
        f"AI Message Analyses: {message}"
    )
    if name or phone or email or message:
        results.append(_send(agent, "+201120853940", text2, dry_run))

    # Route 3: Tawk.to enriched
    if _contains(source, "Tawk.to"):
        text3 = (
            "FTS Travels Automation Team \n"
            "📢 New_Requests_Alert! 🚀 \n"
            f"📍 Request Details: {source} \n"
            f"User Message: \n{message} \n"
            f"AI_response_ suggest: \n{ai_response} \n"
            f"Email: {sender_email} \n"
            f"Phone: {sender_phone} \n"
            f"Intent: {intent} \n"
            f"Chat_id: {chat_id} \n"
            f"Sender_name: {sender_name}"
        )
        results.append(_send(agent, "+201010323484", text3, dry_run))

    # Route 4: generic source alert
    if source:
        text4 = (
            "FTS Travels Automation Team \n"
            "📢 New_Requests_Alert! 🚀 \n"
            f"📍 Request Details: {source} \n"
            f"User Message: \n{message} \n"
            f"AI_response_ suggest: \n{ai_response} \n"
            f"Email: {sender_email} \n"
            f"Phone: {sender_phone} \n"
            f"Intent: {intent} \n"
            f"Chat_id: {chat_id} \n"
            f"Sender_name: {sender_name}"
        )
        results.append(_send(agent, "+201061029883", text4, dry_run))

    return results


def _handle_ceo_report(agent, data: dict, dry_run: bool):
    results = []
    file_name = str(data.get("fileName") or data.get("file_name") or "")
    file_url = str(data.get("fileUrl") or data.get("file_url") or "")
    message = str(data.get("message") or "")
    dynamic_phone = str(data.get("phone_number") or data.get("phone") or "")

    def report_text(who: str) -> str:
        return (
            f"Hello [{who}],\n\n"
            "I hope you're doing well.\n\n"
            "Here is the Daily Report for today:\n"
            f"{file_name}\n{file_url}"
        )

    # Primary CEO-style recipients with Report_Standard filter where Make had it
    results.append(_send(agent, "201010323484", report_text("MR/ Ahmady"), dry_run))

    if dynamic_phone and (not _contains(message, "Backup")) and (not _contains(file_name, "Report_Standard")):
        text = (
            "Hello Mr/Ahmed Elkhatib👋\n\n"
            "I hope you're doing well.\n\n"
            "Here is the daily report link, which is available live 24/7 for access anytime:\n"
            "https://report.tourcare.ai"
        )
        results.append(_send(agent, dynamic_phone, text, dry_run))

    results.append(
        _send(
            agent,
            "+201111178255",
            (
                "Hello Mr/Saada 👋\n\n"
                "I hope you're doing well.\n\n"
                "Here is the daily report link, which is available live 24/7 for access anytime:\n"
                "https://report.tourcare.ai/\n\n"
                "Username: nile\nPassword: nilepassword"
            ),
            dry_run,
        )
    )

    if (not _contains(message, "Backup")) and _contains(file_name, "Report_Standard"):
        results.append(_send(agent, "+201008273178", report_text("MR/ Karim Alaa"), dry_run))

    for phone, who in [
        ("+201027722864", "MR/ M Fawzy"),
        ("+201068177086", "MR/ Farouk Eladawy"),
        ("+201094437167", "MR/ Team"),
        ("+201061029883", "MR/ Ops"),
    ]:
        results.append(_send(agent, phone, report_text(who), dry_run))

    return results


def _handle_daily_report_group(agent, data: dict, dry_run: bool):
    results = []
    file_name = str(data.get("fileName") or data.get("file_name") or "")
    file_url = str(data.get("fileUrl") or data.get("file_url") or "")
    text = (
        "📊 Daily Report Group\n\n"
        f"{file_name}\n{file_url}".strip()
    )
    if not text or text == "📊 Daily Report Group":
        text = str(data.get("text") or data.get("message") or "Daily report update").strip()

    scenario = _find_by_slug("daily_report_group")
    phones = list((scenario or {}).get("phones") or [])
    if not phones:
        phones = ["+201010323484"]
    for phone in phones:
        results.append(_send(agent, phone, text, dry_run))
    return results


def run(agent, payload=None):
    payload = payload or {}
    slug = str(
        payload.get("webhook_slug")
        or payload.get("slug")
        or payload.get("scenario_id")
        or ""
    ).strip().lower()
    # normalize scenario ids to slugs
    if slug.startswith("int_notify_"):
        if "aegypten" in slug:
            slug = "aegypten_requests"
        elif "ceo_report" in slug:
            slug = "ceo_report"
        elif "daily_report" in slug:
            slug = "daily_report_group"

    dry_run = bool(payload.get("dry_run", False))
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload

    if slug in {"aegypten_requests", "aegypten"}:
        results = _handle_aegypten(agent, data, dry_run)
    elif slug in {"ceo_report", "ceo"}:
        results = _handle_ceo_report(agent, data, dry_run)
    elif slug in {"daily_report_group", "daily_report"}:
        results = _handle_daily_report_group(agent, data, dry_run)
    else:
        return {"ok": False, "error": f"unknown_webhook_slug:{slug}", "sent": False}

    sent = any(bool(r.get("ok")) for r in results)
    return {
        "ok": True,
        "sent": sent,
        "slug": slug,
        "dry_run": dry_run,
        "results": results,
    }
