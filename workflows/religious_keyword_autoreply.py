"""
Workflow: Religious Keyword Auto-Reply - ديني
=============================================
الرد التلقائي اللحظي على رسائل عملاء القسم الديني (Religious) بناءً على
قواعد الكلمات المفتاحية (Strict Q/A Rules) المخزنة في knowledge.db.

المنطق (كما طلب المدير - حرفياً):
  1) عند وصول أي رسالة جديدة من العميل (trigger: message_received):
     - يتم فحص نص الرسالة فوراً.
  2) القسم المستهدف: Religious فقط (فلترة صارمة - لا يمس أي قسم آخر).
  3) البحث عن قاعدة مطابقة في جدول strict_qa_rules عبر المحرك الرسمي
     kb.find_strict_qa_match (normalized_exact ثم contains - نفس منطق النظام).
  4) إذا وُجدت قاعدة → يُرسل الرد الجاهز فوراً للعميل
     (متجاوزاً وضع الدرافت لأن القاعدة مُعتمدة مسبقاً من الإدارة).
  5) يُسجَّل الرد في سجل المحادثة chat_history.db.
  6) حماية الحالة: حجز ذري (Atomic Claim) في قاعدة SQLite محلية يمنع
     تكرار الإرسال حتى لو وصلت نفس رسالة العميل أكثر من مرة من فيسبوك
     (Webhook duplicate deliveries) أو من أكثر من تشغيل متزامن.

ملاحظات هندسية (لماذا هذه الشروط):
  - المطابقة دقيقة وحرفية (EXACT): نستخدم المحرك الرسمي كما هو دون أي
    توحيد للهمزات (إ/أ/آ) أو الأرقام أو التاء المربوطة.
    المحرك الرسمي يتجاهل فقط الرموز غير الحرفية (إيموجي، نقاط، علامات
    استفهام/تعجب) لأن knowledge_base._normalize_rule_text يحذف الرموز
    غير الحرفية قبل المقارنة — هذا هو السلوك المطلوب حرفياً من المدير:
    "التطابق بالكلمة 100% حتى لو فيها إيموجي أو نقطة" وليس تطابقاً مرناً.
  - تم تخطي نافذة الـ 24 ساعة تلقائياً لأن هذا رد مباشر (RESPONSE)
    على رسالة العميل الواردة حالاً وليس رسالة برومو مستقلة.
  - احترام auto_reply_hold_until و needs_help: لا نتداخل مع موظف بشري.
  - تجاهل رسائل الميديا غير النصية (صوت/فيديو/ستيكر/مستند).
"""

import os
import json
import re
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta

from fts_paths import get_data_path

# ملف الحالة الاحتياطي (يُستخدم فقط لو تعطلت قاعدة البيانات)
STATE_FILE = get_data_path("religious_keyword_autoreply_state.json")

# قاعدة بيانات الحالة الذرية (Atomic Dedup) - تُنشأ بجانب قاعدة المحادثات
DEDUP_DB = get_data_path("religious_keyword_autoreply_dedup.db")

# أقصى عدد سجلات محفوظة في ملف الحالة الاحتياطي (منع نمو الملف بلا حدود)
MAX_STATE_RECORDS = 2000

# مهلة منع التكرار: إذا أُرسل نفس الرد لنفس المحادثة خلال هذه المدة نتجاهل (بالثواني)
# السبب: فيسبوك يُرسل أحياناً نفس رسالة العميل أكثر من مرة (Webhook duplicate deliveries)
# بنفس النص ومعرفات (mid) مختلفة، فنحتاج حماية ذرية تمنع الإرسال المتكرر.
DEDUP_WINDOW_SECONDS = 600

log = logging.getLogger("ReligiousKeywordAutoReply")


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


def _dedup_key(chat_id: str, external_id: str, message_body: str) -> str:
    """مفتاح تفرد احتياطي: معرف الرسالة الخارجي إن وُجد، وإلا chat_id + نص مختصر."""
    if external_id:
        return f"ext:{external_id}"
    return f"{chat_id}:{str(message_body or '')[:60]}"


def _normalize_body_for_dedup(message_body: str) -> str:
    """
    توحيد نص الرسالة لمنع التكرار فقط (وليس للمطابقة):
    يزيل الإيموجي وعلامات الترقيم والنقاط بنفس طريقة المحرك الرسمي
    (حذف [^\\w\\s]) بحيث تُعتبر "أقرب رحلة متاحة 🚀" و "أقرب رحلة متاحة."
    رسالة واحدة لنفس المحادثة خلال نافذة منع التكرار.
    ملاحظة: لا نوحّد الهمزات هنا أيضاً (مطابقة دقيقة حتى في منع التكرار).
    """
    try:
        s = str(message_body or "").strip().lower()
        # إزالة علامات التشكيل العربية والتطويل
        s = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
        # إزالة كل ما ليس حرفاً أو رقماً (يمحو الإيموجي والترقيم)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        return s.strip()
    except Exception:
        return str(message_body or "").strip()


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
                CREATE TABLE IF NOT EXISTS religious_reply_dedup (
                    dedup_key TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    replied_at TEXT NOT NULL,
                    rule_id TEXT
                )
                """
            )
            conn.commit()
    except Exception as e:
        log.error(f"Failed to init dedup table: {e}")


def _claim_reply(chat_id: str, external_id: str, message_body: str, rule_id: str = None) -> bool:
    """
    محاولة حجز (Claim) حق الرد على هذه الرسالة بشكل ذري.
    تعيد True إذا كان هذا التشغيل هو الأول (يُسمح بالإرسال)،
    و False إذا كانت الرسالة مُعالجة بالفعل (يُمنع الإرسال المكرر).
    المفتاح الموحد يعتمد على المحادثة + النص المطبع (بدون إيموجي/ترقيم)
    وليس على mid المتغير من فيسبوك.
    """
    _ensure_dedup_table()
    # مفتاح موحد: chat_id + hash للنص المطبع (يتجاهل الإيموجي والنقاط)
    try:
        normalized = _normalize_body_for_dedup(message_body)
        body_hash = hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()[:24]
    except Exception:
        body_hash = "0" * 24
    unified_key = f"{chat_id}:{body_hash}"
    now = datetime.utcnow().isoformat()
    try:
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.cursor()
            # حذف السجلات القديمة (أقدم من النافذة) للحفاظ على صغر الجدول
            try:
                cutoff = (datetime.utcnow() - timedelta(seconds=DEDUP_WINDOW_SECONDS)).isoformat()
                cur.execute("DELETE FROM religious_reply_dedup WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            # INSERT OR IGNORE: إذا كان المفتاح موجوداً بالفعل فلن يُدرج => منع التكرار
            cur.execute(
                "INSERT OR IGNORE INTO religious_reply_dedup (dedup_key, chat_id, replied_at, rule_id) VALUES (?, ?, ?, ?)",
                (unified_key, str(chat_id or ""), now, str(rule_id or "")),
            )
            conn.commit()
            claimed = cur.rowcount > 0
        return claimed
    except Exception as e:
        log.error(f"Failed to claim dedup: {e}")
        # في حال فشل قاعدة البيانات، نعود للملف الاحتياطي
        return _legacy_claim(chat_id, external_id, message_body)


def _legacy_claim(chat_id: str, external_id: str, message_body: str) -> bool:
    """حجز احتياطي عبر ملف JSON (لحالات تعطل قاعدة البيانات)."""
    state = _load_state()
    processed = state.get("processed", [])
    key = _dedup_key(chat_id, external_id, message_body)
    if key in processed:
        return False
    processed.append(key)
    if len(processed) > MAX_STATE_RECORDS:
        processed = processed[-MAX_STATE_RECORDS:]
    state["processed"] = processed
    _save_state(state)
    return True


# =============================================================================
# دوال مساعدة
# =============================================================================
def _is_non_text_media(message_body: str) -> bool:
    """هل الرسالة وسائط غير نصية (لا تحمل نصاً للمطابقة)؟"""
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
    تمت إضافة هذا الشرط حتى لا يتعارض الرد الآلي مع تدخل الموظف البشري
    (نفس سلوك المسار الرئيسي: needs_help=1 يوقف الرد الآلي).
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
            now = datetime.fromisoformat(chat_db.get_cairo_time())
            if now.tzinfo is not None:
                now = now.replace(tzinfo=None)
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


def _add_signature_if_needed(agent, text: str, chat_id: str, location: str, source: str = None) -> str:
    """إضافة التوقيع المعتمد (مع خالص التحية) كما يفعل المسار الرئيسي."""
    try:
        if not text:
            return text
        # Religious Meta WhatsApp: plain reply — strip Farah / sales signatures, add nothing
        if getattr(agent, "_is_religious_meta_whatsapp", None) and agent._is_religious_meta_whatsapp(
            chat_id=chat_id, location=location, source=source
        ):
            if getattr(agent, "_strip_religious_whatsapp_closing_artifacts", None):
                return agent._strip_religious_whatsapp_closing_artifacts(text)
            return agent._ensure_signature_once(
                text, "", chat_id=chat_id, location=location, source=source or "WhatsApp"
            )
        assistant_name, assistant_signature = agent._assistant_identity_for_text(text)
        if location and str(location).lower() == "religious":
            owner_name = None
            try:
                import chat_db
                conv = chat_db.get_conversation_info(chat_id) if chat_id else None
                owner_name = conv.get("lead_owner_name") if conv else None
                owner_user_id = conv.get("lead_owner_user_id") if conv else None
                if owner_user_id:
                    owner_name = chat_db.get_user_arabic_name(owner_user_id, owner_name)
            except Exception:
                owner_name = None
            assistant_name = f"مسؤول المبيعات {owner_name}" if owner_name else "مسؤول المبيعات"
            assistant_signature = f"مع خالص التحية،\n{assistant_name}"
        return agent._ensure_signature_once(text, assistant_signature, chat_id=chat_id, location=location, source=source)
    except Exception:
        return text


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

    # ===== فلترة صارمة: القسم الديني فقط (لا نلمس أي قسم آخر) =====
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

    # ===== البحث عن قاعدة الكلمات المفتاحية (المحرك الرسمي - مطابقة دقيقة) =====
    # المطابقة دقيقة وحرفية: نفس منطق النظام تماماً (normalized_exact ثم contains).
    # المحرك الرسمي يتجاهل الإيموجي والنقاط وعلامات الترقيم تلقائياً
    # (يحذف الرموز غير الحرفية) لكنه لا يوحد الهمزات أو الأرقام — مطابقة 100% بالكلمة.
    kb = getattr(agent, "kb", None)
    rule = None
    if kb is not None:
        try:
            rule = kb.find_strict_qa_match(message_body, department="Religious")
        except Exception as e:
            log.error(f"Strict Q/A lookup failed: {e}")
    if not rule:
        # لا توجد قاعدة مطابقة → يترك النظام الأساسي (AI) يتعامل مع الرسالة
        return {"ok": True, "skipped": "no_rule_match", "chat_id": chat_id}

    answer = str(rule.get("answer") or "").strip()
    if not answer:
        return {"ok": True, "skipped": "empty_answer", "chat_id": chat_id}

    # إضافة التوقيع المعتمد للقسم الديني (مطابقة لسلوك المسار الرئيسي)
    answer = _add_signature_if_needed(agent, answer, chat_id, location, source=source)

    # ===== منع التكرار (الحجز الذري) - بعد تحديد القاعدة وقبل الإرسال =====
    # الـ claim يعتمد على مفتاح موحد (chat_id + hash النص المطبع) وليس على
    # mid المتغير من فيسبوك، حتى لو وصلت نفس الرسالة أكثر من مرة خلال النافذة
    # الزمنية. كما يتجاهل الإيموجي والنقاط في النص لمنع التكرار.
    claimed = _claim_reply(chat_id, incoming_external_message_id, message_body, rule.get("id") if rule else None)
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
                text=answer,
                location=location,
                receiving_phone_id=receiving_phone_id,
            )
        else:
            channel = "Facebook"
            ok, error = agent.send_facebook_message(sender_identifier, text=answer)
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
            "rule_id": rule.get("id"),
            "error": str(error)[:500],
        }

    # ===== تسجيل الرد في سجل المحادثة =====
    try:
        import chat_db
        chat_db.add_message(
            chat_id=chat_id,
            sender_type="agent",
            text=answer,
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
                    reason="religious_keyword_autoreply",
                )
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Failed to log reply message: {e}")

    return {
        "ok": True,
        "sent": True,
        "chat_id": chat_id,
        "rule_id": rule.get("id"),
        "matched_question": rule.get("question"),
        "channel": channel,
        "reply_preview": answer[:120],
    }
