# -*- coding: utf-8 -*-
"""
send_ahmed1_campaign.py
=======================
حملة إرسال تمبلت واتساب "ahmed1" من رقم FTS Travels Hajj
(Phone Number ID: 1214164541774422 — قسم Religious)
إلى قائمة أرقام محددة من طلب المدير.

- التمبلت: ahmed1 (اللغة en) — WABA Religious
- الإرسال: Meta Cloud API عبر agent.send_whatsapp_message
- المحادثات تُنشأ/تُحدَّث في chat_history.db (source=WhatsApp, location=Religious)
- جميع المحادثات تُخصص للمستخدم أحمد خليل (user_id=17 / Ahmed_Khalil)
  حتى يرد عليها هو فقط من لوحة التحكم (lead_owner_user_id='17').

طريقة التشغيل (بدون إعادة تشغيل السيرفر):
    POST http://127.0.0.1:5001/api/automation/run_script
    {"script_name": "send_ahmed1_campaign.py"}
"""

import os
import time
import logging
from datetime import datetime

log = logging.getLogger("send_ahmed1_campaign")

# =============================================================================
# قائمة الأرقام (من طلب المدير — بنفس الترتيب، مع إزالة التكرار +201001628232)
# =============================================================================
TARGET_PHONES = [
    "201004411417",
    "201112755213",
    "201019304511",
    "201157066670",
    "201229681131",
    "201004671506",
    "201156795434",
    "201002030435",
    "201226908389",
    "201001987004",
    "201001628232",
    "201112349131",
    "201001691643",
    "201004386096",
    "201277757942",
    "201155333483",
    "201097954056",
    "201150065696",
    "201064475109",
    "201224404458",
    "201272700897",
    "201014875549",
    "201094546724",
    "201120055770",
    "201023246311",
]

RECEIVING_PHONE_ID = "1214164541774422"   # FTS Travels Hajj (Religious)
TEMPLATE_NAME = "ahmed1"
TEMPLATE_LANGUAGE = "en"
LOCATION = "Religious"

# المستخدم المخصص للحملة: أحمد خليل (قسم Religious)
OWNER_USER_ID = "17"
OWNER_USERNAME = "Ahmed_Khalil"
OWNER_NAME = "أحمد خليل"


def _clean_phone(v) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def _dedupe(phones):
    seen = set()
    out = []
    for p in phones:
        c = _clean_phone(p)
        if not c:
            continue
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _ensure_conversation(phone: str):
    """إنشاء/تحديث محادثة واتساب في chat_history.db وتخصيصها لأحمد خليل."""
    import chat_db

    conv = chat_db.find_whatsapp_conversation_by_phone(phone)
    if not conv:
        conv = chat_db.get_or_create_conversation(
            source="WhatsApp",
            sender_identifier=phone,
            contact_name=phone,
            location=LOCATION,
            thread_id="",
            receiving_phone_id=RECEIVING_PHONE_ID,
        ) or {}
    chat_id = str(conv.get("chat_id") or "").strip()
    if not chat_id:
        return None, "no_chat_id"

    # التخصيص لأحمد خليل فقط (حتى تظهر المحادثة عنده في لوحة Religious)
    import sqlite3
    with sqlite3.connect(chat_db.DB_FILE, timeout=15.0) as conn:
        c = conn.cursor()
        c.execute(
            """
            UPDATE conversations
            SET lead_owner_user_id = ?,
                lead_owner_name = ?,
                assigned_to = ?,
                receiving_phone_id = COALESCE(NULLIF(receiving_phone_id, ''), ?),
                location = COALESCE(NULLIF(location, ''), ?)
            WHERE chat_id = ?
            """,
            (OWNER_USER_ID, OWNER_NAME, OWNER_USERNAME, RECEIVING_PHONE_ID, LOCATION, chat_id),
        )
        conn.commit()
    return chat_id, None


def run(agent, payload: dict = None) -> dict:
    """
    نقطة الدخول — يستدعيها محرك الأتمتة /api/automation/run_script.
    payload اختياري:
      - phones: قائمة أرقام بديلة
      - dry_run: محاكاة فقط دون إرسال حقيقي
      - max_sends: حد أقصى لعدد الإرسالات (للاختبار)
    """
    payload = payload or {}
    phones = _dedupe(payload.get("phones") or TARGET_PHONES)
    dry_run = bool(payload.get("dry_run", False))
    max_sends = int(payload.get("max_sends") or 0) or len(phones)
    delay_sec = float(payload.get("delay_sec") or 1.5)

    results = []
    sent_ok = 0
    sent_fail = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, phone in enumerate(phones[:max_sends]):
        chat_id, err = _ensure_conversation(phone)
        if err or not chat_id:
            results.append({"phone": phone, "status": "error", "step": "ensure_conversation", "error": err})
            sent_fail += 1
            continue

        if dry_run:
            results.append({
                "phone": phone, "status": "dry_run",
                "chat_id": chat_id,
                "template": TEMPLATE_NAME,
                "receiving_phone_id": RECEIVING_PHONE_ID,
                "owner": OWNER_NAME,
            })
            continue

        ok = False
        meta = None
        try:
            ok, meta = agent.send_whatsapp_message(
                phone,
                text="",
                location=LOCATION,
                template_name=TEMPLATE_NAME,
                template_language=TEMPLATE_LANGUAGE,
                receiving_phone_id=RECEIVING_PHONE_ID,
            )
        except Exception as e:
            ok = False
            meta = str(e)

        # تسجيل محاولة الإرسال داخل المحادثة
        try:
            import chat_db
            body = ""
            if isinstance(meta, dict):
                body = str(meta.get("body") or meta.get("error") or "")[:300]
            status_txt = "sent" if ok else "error"
            header = f"[Campaign ahmed1] Template '{TEMPLATE_NAME}'"
            if not ok:
                header += f" FAILED — {body}"
            chat_db.add_message(
                chat_id=chat_id,
                sender_type="agent",
                text=header,
                status=status_txt,
                increment_unread=False,
                source="WhatsApp",
            )
        except Exception as e:
            log.warning(f"Failed to log send for {phone}: {e}")

        if ok:
            sent_ok += 1
        else:
            sent_fail += 1
            body = ""
            if isinstance(meta, dict):
                body = str(meta.get("body") or "")[:400]
            log.warning("Send failed for %s: %s", phone, body)

        results.append({
            "phone": phone,
            "status": "success" if ok else "error",
            "chat_id": chat_id,
            "template": TEMPLATE_NAME,
            "receiving_phone_id": RECEIVING_PHONE_ID,
            "owner": OWNER_NAME,
            "meta": meta if isinstance(meta, dict) else None,
        })

        if idx < len(phones[:max_sends]) - 1 and not dry_run:
            time.sleep(delay_sec)

    return {
        "status": "success",
        "data": {
            "script": "send_ahmed1_campaign.py",
            "run_at": now_str,
            "total_targeted": len(phones),
            "processed": len(results),
            "sent_ok": sent_ok,
            "sent_fail": sent_fail,
            "dry_run": dry_run,
            "template": TEMPLATE_NAME,
            "template_language": TEMPLATE_LANGUAGE,
            "receiving_phone_id": RECEIVING_PHONE_ID,
            "location": LOCATION,
            "owner_user_id": OWNER_USER_ID,
            "owner_name": OWNER_NAME,
            "results": results,
        },
    }
