"""
Workflow: "وصلني رقمك" Religious Auto-Reply - ديني (العميل أرسل رقم تليفونه)
=============================================================================================
طلب المدير (2026-08-31):
  - الرسالة التالية تُرسل للعميل الذي يرسل رقم تليفونه (يكتب الرقم في الرسالة):
      "الغي الموضوع ده تمام يا فندم، وصلني رقم حضرتك 🧡 هيتواصل معاك على الواتساب
       في أقرب وقت بكل تفاصيل البرامج والخصم. شكرًا لثقة حضرتك في FTS للسياحة،
       وربنا يكتبلك الحج 🕋"

القرارات الهندسية (مطابقة لنفس سلوك الـ Workflows المعتمدة في النظام):
  - trigger_type = "message_received" (رد لحظي مباشر على رسالة العميل الواردة).
  - الكشف عن "رقم التليفون" داخل نص الرسالة عبر Regex (وليس مطابقة كلمة):
      * أرقام مصرية محلية: 01[0125] + 8 أرقام (11 رقمًا) — مع منع المطابقة داخل
        رقم أطول (Lookbehind/Lookahead) حتى لا يخطئ في قراءة الرقم القومي
        (14 رقمًا يبدأ بـ 30 مثلاً) كرقم تليفون.
      * الصيغة الدولية: +20 / 0020 + 1xxxxxxxxx (مع السماح بـ 0 قبل الـ 1).
      * تحويل الأرقام الهندية (٠-٩) والفارسية (۰-۹) إلى أرقام لاتينية أولاً
        (كثير من العملاء يكتبون الرقم بأرقام عربية).
      * السماح بالمسافات والشرطات بين الأرقام (010 1234 5678 / 010-1234-5678).
  - القسم المستهدف: Religious فقط (الرد يتحدث عن برامج الحج "ربنا يكتبلك الحج" ⇒
    فلترة صارمة من الجذور location == Religious — قاعدة النظام 15: لا نلمس أي قسم آخر).
  - الرد المباشر يخطي نافذة Meta الـ 24 ساعة تلقائياً (رد RESPONSE وليس برومو مستقل).
  - إرسال الرد مرة واحدة فقط لكل (محادثة + رقم تليفون) خلال نافذة منع التكرار
    (حجز ذري Atomic Claim يمنع التكرار من Webhook duplicate deliveries، ويحمي
    العميل من إزعاج التكرار لو أرسل نفس الرقم أكثر من مرة).
  - احترام auto_reply_hold_until و needs_help (لا نتداخل مع موظف بشري).
  - تجاهل رسائل الميديا غير النصية (صوت/فيديو/ستيكر/مستند/موقع).
  - كل تواريخ المقارنة تستخدم توقيت القاهرة chat_db.get_cairo_time() وليس utcnow
    (قاعدة النظام F — نظام FTS يخزن التوقيت كله بتوقيت القاهرة UTC+3).
  - إدارة الحالة عبر ملف JSON محلي + قاعدة بيانات Dedup مستقلة (لا نستخدم
    agent.load_state / save_state — قاعدة النظام G).
  - لا حاجة لإعادة تشغيل السيرفر: محرك الأتمتة يقرأ automation_workflows في كل
    tick (hot-load) — لا نلمس ai_agent.py إطلاقاً.
"""

import os
import re
import json
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ⚙️ الرد الثابت المعتمد (منسوخ حرفياً من طلب المدير 2026-08-31)
# =============================================================================
# IMPORTANT: النص منسوخ حرفياً مع الحفاظ على النص العربي والإيموجي وعلامات الترقيم.
REPLY_TEXT = (
    "الغي الموضوع ده تمام يا فندم، وصلني رقم حضرتك 🧡 "
    "هيتواصل معاك على الواتساب في أقرب وقت بكل تفاصيل البرامج والخصم. "
    "شكرًا لثقة حضرتك في FTS للسياحة، وربنا يكتبلك الحج 🕋"
)

# ملف الحالة الاحتياطي (يُستخدم فقط لو تعطلت قاعدة البيانات)
STATE_FILE = get_data_path("client_sent_phone_number_autoreply_state.json")

# قاعدة بيانات الحالة الذرية (Atomic Dedup) - مستقلة تماماً عن أي سكربت آخر
DEDUP_DB = get_data_path("client_sent_phone_number_autoreply_dedup.db")

# أقصى عدد سجلات محفوظة في ملف الحالة الاحتياطي (منع نمو الملف بلا حدود)
MAX_STATE_RECORDS = 2000

# مهلة منع التكرار: إذا أُرسل نفس الرد لنفس (المحادثة + الرقم) خلال هذه المدة نتجاهل
# السبب: فيسبوك يُرسل أحياناً نفس رسالة العميل أكثر من مرة (Webhook duplicate
# deliveries)، كما يحمي العميل من إزعاج تكرار الإرسال لو أرسل نفس الرقم أكثر من مرة.
DEDUP_WINDOW_SECONDS = 600

log = logging.getLogger("ClientSentPhoneNumberAutoReply")


# =============================================================================
# أدوات الحالة المحلية (State Management - يمنع استخدام agent.load_state)
# =============================================================================
def _load_state() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception as e:
        log.error(f"Failed to load state: {e}")
    return {}


def _save_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except Exception as e:
        log.error(f"Failed to save state: {e}")


def _cairo_now_iso() -> str:
    """
    الوقت الحالي بتوقيت القاهرة (UTC+3) — نفس توقيت النظام كله (قاعدة النظام F).
    تُستخدم في كل مقارنات الوقت داخل السكربت، وليس utcnow أبداً.
    """
    try:
        import chat_db
        now = datetime.fromisoformat(chat_db.get_cairo_time())
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        return now.isoformat()
    except Exception:
        return datetime.utcnow().isoformat()


# =============================================================================
# كشف رقم التليفون في نص الرسالة (Regex)
# =============================================================================
def _to_latin_digits(text: str) -> str:
    """تحويل الأرقام الهندية (٠١٢٣٤٥٦٧٨٩) والفارسية (۰۱۲۳۴۵۶۷۸۹) إلى لاتينية."""
    try:
        for frm, to in (("٠١٢٣٤٥٦٧٨٩", "0123456789"), ("۰۱۲۳۴۵۶۷۸۹", "0123456789")):
            text = text.translate(str.maketrans(frm, to))
    except Exception:
        pass
    return text


def _extract_egyptian_phone(message_body: str) -> str:
    """
    استخراج رقم موبايل مصري من نص الرسالة، أو None إن لم يوجد.
    - Local: 01[0125] + 8 أرقام = 11 رقمًا (لا يسبقه أو يليه رقم آخر حتى لا
      يُقرأ الرقم القومي 14 رقمًا كرقم تليفون).
    - Intl : (0020 أو 20) + 1[0125] + 8 أرقام — مع السماح بـ 0 اختياري قبل الـ 1
      (مثل +20 01012345678) وتجاهل المسافات/الشرطات.
    - المسافات والشرطات والنقاط بين الأرقام تُحذف قبل الفحص.
    """
    try:
        text = _to_latin_digits(str(message_body or ""))
    except Exception:
        text = str(message_body or "")
    # توحيد: حذف كل ما ليس رقماً (يزيل المسافات والشرطات والنقاط وعلامة +)
    digits_only = re.sub(r"[^\d]", "", text)
    if not digits_only:
        return None
    # الصيغة المحلية: 11 رقمًا تبدأ بـ 01 (010/011/012/015)
    m = re.search(r"(?<!\d)(01[0125]\d{8})(?!\d)", digits_only)
    if m:
        return m.group(1)
    # الصيغة الدولية: 20/0020 متبوعة بـ 1xxxxxxxxx (مع 0 اختيارية قبل الـ 1)
    m = re.search(r"(?<!\d)((?:0020|20)0?1[0125]\d{8})(?!\d)", digits_only)
    if m:
        raw = m.group(1)
        # توحيد إلى الصيغة المحلية 01xxxxxxxxx للتخزين/منع التكرار:
        # نزيل بادئة الدولة (0020 أو 20) ثم نضمن وجود 0 في البداية
        body = raw
        if body.startswith("0020"):
            body = body[4:]
        elif body.startswith("20"):
            body = body[2:]
        if body and not body.startswith("0"):
            body = "0" + body
        return body
    return None


# =============================================================================
# منع التكرار الذري (Atomic Claim) - يحل مشكلة السباق بين التشغيلات المتزامنة
# =============================================================================
def _ensure_dedup_table():
    """إنشاء جدول منع التكرار الذري إن لم يكن موجوداً."""
    try:
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS client_sent_phone_reply_dedup (
                    dedup_key TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    replied_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
    except Exception as e:
        log.error(f"Failed to init dedup table: {e}")


def _claim_reply(chat_id: str, phone: str) -> bool:
    """
    محاولة حجز (Claim) حق الرد على (المحادثة + الرقم) بشكل ذري.
    تعيد True إذا كان هذا التشغيل هو الأول (يُسمح بالإرسال)،
    و False إذا كان قد تم الرد بالفعل خلال نافذة منع التكرار.
    """
    _ensure_dedup_table()
    unified_key = f"{chat_id}:{phone}"
    now = _cairo_now_iso()
    try:
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.cursor()
            # حذف السجلات القديمة (أقدم من النافذة) للحفاظ على صغر الجدول
            try:
                from dateutil import parser as _dp
                cutoff_dt = _dp.isoparse(now) - timedelta(seconds=DEDUP_WINDOW_SECONDS)
                cutoff = cutoff_dt.isoformat()
            except Exception:
                cutoff = (datetime.utcnow() - timedelta(seconds=DEDUP_WINDOW_SECONDS)).isoformat()
            try:
                cur.execute("DELETE FROM client_sent_phone_reply_dedup WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            # INSERT OR IGNORE: إذا كان المفتاح موجوداً بالفعل فلن يُدرج => منع التكرار
            cur.execute(
                "INSERT OR IGNORE INTO client_sent_phone_reply_dedup (dedup_key, chat_id, phone, replied_at) VALUES (?, ?, ?, ?)",
                (unified_key, str(chat_id or ""), str(phone or ""), now),
            )
            conn.commit()
            claimed = cur.rowcount > 0
        return claimed
    except Exception as e:
        log.error(f"Failed to claim dedup: {e}")
        # في حال فشل قاعدة البيانات، نعود للملف الاحتياطي
        return _legacy_claim(unified_key)


def _legacy_claim(unified_key: str) -> bool:
    """حجز احتياطي عبر ملف JSON (لحالات تعطل قاعدة البيانات)."""
    state = _load_state()
    processed = state.get("processed", [])
    if unified_key in processed:
        return False
    processed.append(unified_key)
    if len(processed) > MAX_STATE_RECORDS:
        processed = processed[-MAX_STATE_RECORDS:]
    state["processed"] = processed
    _save_state(state)
    return True


# =============================================================================
# دوال مساعدة (نفس سلوك الـ Workflows المعتمدة)
# =============================================================================
def _is_non_text_media(message_body: str) -> bool:
    """هل الرسالة وسائط غير نصية (لا تحمل نصاً للكشف عن رقم)؟"""
    lb = str(message_body or "").lower().strip()
    prefixes = (
        "[customer sent an audio message.",
        "[customer sent a video.",
        "[customer sent a sticker.",
        "[customer sent a document.",
        "[customer sent a message of type:",
        "[customer shared a location]",
        "[customer shared contacts.",
    )
    return any(lb.startswith(p) for p in prefixes)


def _is_human_active(chat_id: str) -> bool:
    """
    هل يوجد مساعد بشري نشط في المحادثة (needs_help=1)؟
    تمت إضافة هذا الشرط حتى لا يتعارض الرد الآلي مع تدخل الموظف البشري.
    """
    try:
        import chat_db
        conv = chat_db.get_conversation(chat_id) or {}
        try:
            return int(conv.get("needs_help") or 0) == 1
        except Exception:
            return False
    except Exception:
        return False


def _is_chat_on_hold(chat_id: str) -> bool:
    """هل أوقف إداري الرد الآلي لهذه المحادثة (auto_reply_hold_until)؟"""
    try:
        import chat_db
        conv = chat_db.get_conversation(chat_id) or {}
        hold_raw = str(conv.get("auto_reply_hold_until") or "").strip()
        if not hold_raw:
            return False
        try:
            # استخدام توقيت القاهرة (UTC+3) كما يخزنه النظام كله — لا نستخدم utcnow أبداً
            now = datetime.fromisoformat(_cairo_now_iso())
            hold_dt = datetime.fromisoformat(hold_raw)
            if hold_dt.tzinfo is not None:
                hold_dt = hold_dt.replace(tzinfo=None)
            # إذا كانت فترة الإيقاف ما زالت سارية → لا نرسل
            if hold_dt > now:
                return True
            # انتهت الفترة → نلغي الإيقاف ونسمح بالإرسال
            try:
                chat_db.update_auto_reply_hold_until(chat_id, None)
            except Exception:
                pass
        except Exception:
            return False
    except Exception:
        pass
    return False


# =============================================================================
# نقطة الدخول الرئيسية (يستدعيها محرك الأتمتة)
# =============================================================================
def run(agent, payload: dict = None) -> dict:
    """
    المعاملات (payload) قادمة من حدث message_received:
      chat_id, message_body, sender_identifier, source, location,
      receiving_phone_id, incoming_external_message_id
    """
    payload = payload or {}
    chat_id = str(payload.get("chat_id") or "").strip()
    message_body = str(payload.get("message_body") or "").strip()
    source = str(payload.get("source") or "").strip()
    sender_identifier = str(payload.get("sender_identifier") or "").strip()
    location = str(payload.get("location") or "").strip()
    receiving_phone_id = str(payload.get("receiving_phone_id") or "").strip() or None
    incoming_external_message_id = str(payload.get("incoming_external_message_id") or "").strip()

    # ===== فلترة صارمة من الجذور: القسم الديني فقط (لا نلمس أي قسم آخر) =====
    # قاعدة النظام 15: الرد يتحدث عن برامج الحج ("ربنا يكتبلك الحج") ⇒ يُمنع
    # تماماً إرساله لأي قسم آخر (Hurghada / Sharm / Sales / Drivers ...).
    if location.lower() != "religious":
        return {"ok": True, "skipped": "not_religious", "chat_id": chat_id}

    if not chat_id or not message_body or not sender_identifier:
        return {"ok": True, "skipped": "missing_data", "chat_id": chat_id}

    # ===== تجاهل رسائل الميديا غير النصية =====
    if _is_non_text_media(message_body):
        return {"ok": True, "skipped": "non_text_media", "chat_id": chat_id}

    # ===== احترام إيقاف الإداري للرد الآلي على هذه المحادثة =====
    if _is_chat_on_hold(chat_id):
        return {"ok": True, "skipped": "human_hold", "chat_id": chat_id}

    # ===== لا نتداخل مع مساعد بشري نشط (needs_help=1) =====
    if _is_human_active(chat_id):
        return {"ok": True, "skipped": "human_active", "chat_id": chat_id}

    # ===== الكشف عن رقم التليفون داخل نص الرسالة =====
    phone = _extract_egyptian_phone(message_body)
    if not phone:
        # لا يوجد رقم تليفون في الرسالة → يترك النظام الأساسي (AI) يتعامل معها
        return {"ok": True, "skipped": "no_phone_found", "chat_id": chat_id}

    # ===== منع التكرار (الحجز الذري) - بعد تحديد الرقم وقبل الإرسال =====
    claimed = _claim_reply(chat_id, phone)
    if not claimed:
        return {"ok": True, "skipped": "already_processed", "chat_id": chat_id}

    # ===== الإرسال الفوري عبر القناة الصحيحة =====
    channel = source if source else "Facebook"
    ok = False
    error = None
    try:
        if str(source).lower() == "whatsapp" or str(sender_identifier).startswith("20"):
            channel = "WhatsApp"
            ok, error = agent.send_whatsapp_message(
                sender_identifier,
                text=REPLY_TEXT,
                location=location,
                receiving_phone_id=receiving_phone_id,
            )
        else:
            channel = "Facebook"
            ok, error = agent.send_facebook_message(sender_identifier, text=REPLY_TEXT)
    except Exception as e:
        ok = False
        error = str(e)
        log.error(f"Send error: {e}")

    if not ok:
        log.warning(f"Send failed for chat {chat_id}: {error}")
        return {
            "ok": False,
            "skipped": "send_failed",
            "chat_id": chat_id,
            "phone": phone,
            "error": str(error)[:500],
        }

    # ===== تسجيل الرد في سجل المحادثة =====
    try:
        import chat_db
        chat_db.add_message(
            chat_id=chat_id,
            sender_type="agent",
            text=REPLY_TEXT,
            status="sent",
            source=channel,
        )
        try:
            chat_db.mark_conversation_read(chat_id)
        except Exception:
            pass
        # منع سباق مسار الـ Debounce/AI: احذف أي مسودة وألغِ مؤقت الـ 10 ثوانٍ
        try:
            chat_db.delete_proposed_drafts(chat_id)
        except Exception:
            pass
        try:
            if agent and hasattr(agent, "cancel_whatsapp_ai_processing"):
                agent.cancel_whatsapp_ai_processing(
                    chat_id=chat_id,
                    reason="client_sent_phone_number_autoreply",
                )
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Failed to log reply message: {e}")

    return {
        "ok": True,
        "sent": True,
        "chat_id": chat_id,
        "phone": phone,
        "channel": channel,
        "reply_preview": REPLY_TEXT[:120],
    }
