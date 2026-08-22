# -*- coding: utf-8 -*-
"""
Workflow: Religious All Prices Auto-Reply - ديني (💰 عايز الأسعار كلها)
=============================================================================
Workflow جديد ومستقل 100% — لا يلمس "6 Programs Prices Auto-Reply"
ولا "Hajj Programs Prices WhatsApp Auto-Reply" ولا أي Workflow موجود آخر.
(تمت إضافة كلمة "Religious" و "ديني" في الاسم لتظهر في لوحة المدير الديني
لأن الفلتر في الواجهة يعتمد على كلمة religious/ديني في الاسم — قاعدة النظام D.
والاسم يحتفظ بالعبارة التي طلبها المدير حرفياً: 💰 عايز الأسعار كلها)

المطلوب (من المدير — 2026-08-22):
  اعمل workflow باسم: (💰 عايز الأسعار كلها)
  - لما عميل يبقي الكلمة ديه مطابقة 100% (Exact Match بالظبط) —
    رسالة العميل تساوي الكلمة بالكامل (مساواة كاملة == بعد إزالة الرموز
    غير الحرفية فقط بنفس منطق المحرك الرسمي knowledge_base._normalize_rule_text).
  - ممنوع Contains / StartsWith / EndsWith: أي كلمة إضافية قبل النص أو بعده
    → لا رد.
  - الرد: رسالتين متتاليتين (رسالة 1 ثم رسالة 2 ورا بعض مباشرة) بالنص
    الحرفي التالي كما ورد من المدير (مع الحفاظ على النص والإيموجي
    والأرقام العربية ٢١٠,٠٠٠ ... إلخ وعلامات الترقيم):
      📩 رسالة 1: دي الـ٦ برامج بأسعار الموسم الماضي ... (أسعار الـ٦ برامج)
      📩 رسالة 2: ⭐ والأهم: اللي بيسجل دلوقتي بنحافظله على الخصم بتاعه ...
  - فقط في قسم Religious (فلترة صارمة - لا يمس أي قسم آخر).

القواعد المنفذة (كما طلب المدير + قواعد النظام):
  - المطابقة: Exact Match 100% (الرسالة == الكلمة بالكامل بعد التطبيع الذي
    يحذف الرموز غير الحرفية فقط — لا نوحّد الهمزات ولا الأرقام).
  - القسم المستهدف: Religious فقط (فلترة صارمة - لا يمس أي قسم آخر).
  - الرد مباشرة (لحظي) على رسالة العميل: تخطي نافذة الـ 24 ساعة تلقائياً
    لأن هذا رد مباشر (RESPONSE) على رسالة واردة وليس برومو مستقل.
  - إرسال رسالتين متتاليتين (2 رسائل ورا بعض): الرسالة الأولى ثم الثانية
    بعدها مباشرة بفاصل زمني قصير (2 ثانية) حتى تصل كرسالتين منفصلتين
    في المحادثة تماماً كما طلب المدير — وكل رسالة تُسجل في سجل المحادثة.
  - إرسال الرد مرة واحدة فقط لكل رسالة (حجز ذري Atomic Claim يمنع تكرار
    الإرسال حتى لو وصلت نفس الرسالة من فيسبوك أكثر من مرة / Webhook
    duplicate deliveries) — والـ claim يغطي الرسالتين معاً كحزمة واحدة.
  - احترام auto_reply_hold_until و needs_help: لا نتداخل مع موظف بشري.
  - تجاهل رسائل الميديا غير النصية (صوت/فيديو/ستيكر/مستند).
  - لا نلمس أي قواعد strict_qa_rules ولا knowledge.db إطلاقاً:
    الكلمة المفتاحية والرد معرفان محلياً هنا في هذا الملف.
  - كل التواريخ تُقارن بتوقيت القاهرة chat_db.get_cairo_time() وليس utcnow
    (قاعدة النظام F).
  - إدارة الحالة عبر قاعدة بيانات محلية مستقلة (Atomic Dedup DB) + ملف
    JSON احتياطي — يُمنع استخدام agent.load_state (قاعدة النظام G).
"""

import os
import json
import re
import sqlite3
import hashlib
import time
import logging
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ⚙️ الكلمة المفتاحية والرد الثابت المعتمد (عدّل هنا فقط لإضافة/تعديل الكلمات)
# =============================================================================
# IMPORTANT: النص التالي منسوخ حرفياً من طلب المدير (2026-08-22)
# — مع الحفاظ على النص العربي والإيموجي والأرقام وعلامات الترقيم كما هي.
# "reply_parts" = رسالتان متتاليتان ورا بعض (رسالة 1 ثم رسالة 2).
KEYWORDS = [
    {
        "keyword": "💰 عايز الأسعار كلها",
        "reply_parts": [
            # 📩 رسالة 1
            (
                "دي الـ٦ برامج بأسعار الموسم الماضي (مبنية على برنامج الموسم "
                "السابق — والسعر النهائي بيتأكد بعد صدور ضوابط وزارة السياحة):\n"
                "\n"
                "🚌 الحج البري:\n"
                "1️⃣ البري — ٢١٠,٠٠٠ ج بدلًا من ٢٢٠,٠٠٠ ج\n"
                "💰 (خصم ١٠,٠٠٠ ج)\n"
                "\n"
                "✈️ برامج الطيران:\n"
                "2️⃣ اقتصادي — ٢٢٠,٠٠٠ ج بدلًا من ٢٤٥,٠٠٠ ج\n"
                "💰 (خصم ٢٥,٠٠٠ ج)\n"
                "\n"
                "3️⃣ تحسين — ٢٥٠,٠٠٠ ج بدلًا من ٢٧٩,٠٠٠ ج\n"
                "💰 (خصم ٢٩,٠٠٠ ج)\n"
                "⭐ + ٧ أيام إقامة على ساحة الحرم بعد المناسك\n"
                "\n"
                "⭐ برامج الـ٥ نجوم:\n"
                "4️⃣ مخيمات ٥ نجوم — ٤٩٠,٠٠٠ ج\n"
                "5️⃣ مخيمات ٥ نجوم صف أول — ٥٥٠,٠٠٠ ج\n"
                "6️⃣ أبراج كدانة — ٦٤٠,٠٠٠ ج\n"
                "\n"
                "🎁 كل الأسعار محسوب فيها خصم الحجز المبكر للمسجلين قبل نزول "
                "الضوابط."
            ),
            # 📩 رسالة 2
            (
                "⭐ والأهم: اللي بيسجل دلوقتي بنحافظله على الخصم بتاعه — حتى "
                "لو الأسعار اتغيرت بعد نزول الضوابط، خصمك محسوبلك من تاريخ "
                "تسجيلك.\n"
                "\n"
                "عشان نثبتلك الخصم، ابعتلنا:\n"
                "📸 صورة البطاقة (وش وضهر)\n"
                "📱 رقم الموبايل\n"
                "\n"
                "وهكلم حضرتك اشرحلك تفاصيل اكتر وأأكد معاك الحجز المبدأي ✅"
            ),
        ],
        "enabled": True,   # مفعّلة
    },
]

# ملف الحالة الاحتياطي (يُستخدم فقط لو تعطلت قاعدة البيانات)
STATE_FILE = get_data_path("religious_all_prices_autoreply_state.json")

# قاعدة بيانات الحالة الذرية (Atomic Dedup) - مستقلة تماماً عن أي سكربت آخر
DEDUP_DB = get_data_path("religious_all_prices_autoreply_dedup.db")

# أقصى عدد سجلات محفوظة في ملف الحالة الاحتياطي (منع نمو الملف بلا حدود)
MAX_STATE_RECORDS = 2000

# مهلة منع التكرار: إذا أُرسل نفس الرد لنفس المحادثة خلال هذه المدة نتجاهل (بالثواني)
# السبب: فيسبوك يُرسل أحياناً نفس رسالة العميل أكثر من مرة (Webhook duplicate deliveries)
# بنفس النص ومعرفات (mid) مختلفة، فنحتاج حماية ذرية تمنع الإرسال المتكرر.
DEDUP_WINDOW_SECONDS = 600

# الفاصل الزمني بين الرسالتين المتتاليتين (بالثواني)
# السبب: نرسل "رسالة 1" ثم "رسالة 2" ورا بعض مباشرة كرسالتين منفصلتين
# تماماً كما طلب المدير — الفاصل القصير يضمن وصولهما كرسالتين مستقلتين
# ولا يدمجهما فيسبوك/واتساب في رسالة واحدة (وكذلك يمنع ترتيب الرسائل العكسي).
INTER_MESSAGE_DELAY_SECONDS = 2

log = logging.getLogger("ReligiousAllPricesAutoReply")


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
    r"""
    توحيد نص الرسالة لمنع التكرار فقط (وليس للمطابقة):
    يزيل الإيموجي وعلامات الترقيم والنقاط بنفس طريقة المحرك الرسمي
    (حذف [^\w\s]) بحيث تُعتبر "💰 عايز الأسعار كلها" و "💰 عايز الأسعار كلها."
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
                CREATE TABLE IF NOT EXISTS religious_all_prices_reply_dedup (
                    dedup_key TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    replied_at TEXT NOT NULL,
                    keyword TEXT
                )
                """
            )
            conn.commit()
    except Exception as e:
        log.error(f"Failed to init dedup table: {e}")


def _claim_reply(chat_id: str, external_id: str, message_body: str, keyword: str = None) -> bool:
    """
    محاولة حجز (Claim) حق الرد على هذه الرسالة بشكل ذري.
    تعيد True إذا كان هذا التشغيل هو الأول (يُسمح بإرسال الرسالتين)،
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
    try:
        import chat_db as _cdb
        now_raw = _cdb.get_cairo_time()
        now = datetime.fromisoformat(now_raw)
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
    except Exception:
        # توقيت القاهرة (UTC+3) بديل آمن لو تعطل chat_db — لا نستخدم utcnow
        now = datetime.utcnow() + timedelta(hours=3)
    now_iso = now.isoformat()
    try:
        with sqlite3.connect(DEDUP_DB, timeout=30.0) as conn:
            conn.execute("PRAGMA busy_timeout = 30000;")
            cur = conn.cursor()
            # حذف السجلات القديمة (أقدم من النافذة) للحفاظ على صغر الجدول
            try:
                cutoff = (now - timedelta(seconds=DEDUP_WINDOW_SECONDS)).isoformat()
                cur.execute("DELETE FROM religious_all_prices_reply_dedup WHERE replied_at < ?", (cutoff,))
            except Exception:
                pass
            # INSERT OR IGNORE: إذا كان المفتاح موجوداً بالفعل فلن يُدرج => منع التكرار
            cur.execute(
                "INSERT OR IGNORE INTO religious_all_prices_reply_dedup (dedup_key, chat_id, replied_at, keyword) VALUES (?, ?, ?, ?)",
                (unified_key, str(chat_id or ""), now_iso, str(keyword or "")),
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
# المطابقة الدقيقة (Exact Keyword Match) - ممنوع Contains/StartsWith/EndsWith
# =============================================================================
def _normalize_for_match(text: str) -> str:
    """
    توحيد النص للمطابقة الدقيقة — نفس سلوك knowledge_base._normalize_rule_text:
      - تحويل لحروف صغيرة
      - حذف التشكيل والتطويل (الـ → ال)
      - حذف الرموز غير الحرفية (إيموجي، نقاط، علامات استفهام/تعجب)
      - توحيد المسافات
    ملاحظة: لا نوحّد الهمزات (إ/أ/آ) ولا الأرقام (0-9 / ٠-٩) — مطابقة 100% بالكلمة.
    """
    try:
        s = str(text or "").strip().lower()
        s = re.sub(r"[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)
        s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
        s = re.sub(r"\s+", " ", s, flags=re.UNICODE)
        return s.strip()
    except Exception:
        return str(text or "").strip().lower()


def _match_keyword(message_body: str):
    """
    المطابقة الدقيقة (EXACT): رسالة العميل يجب أن تساوي الكلمة المحددة بالكامل
    (مساواة كاملة == بعد إزالة الرموز غير الحرفية فقط — نفس منطق المحرك الرسمي).
    - ممنوع Contains: أي كلمة إضافية قبل النص أو بعده تكسر المساواة → لا رد.
    - ممنوع StartsWith / EndsWith.
    - إذا تساوت رسالتان مع كلمتين مختلفتين (مستحيل عملياً) نعيد أول تطابق فقط
      (عدم تشغيل أكثر من رد على الرسالة نفسها).
    مثال تطابقي: "💰 عايز الأسعار كلها" بمفردها → تُطابق (الإيموجي يُحذف
    بالتطبيع) — أما "عايز الأسعار كلها بسرعة" فلا تُطابق (كلمات إضافية).
    """
    normalized_message = _normalize_for_match(message_body)
    if not normalized_message:
        return None
    for entry in KEYWORDS:
        if not entry.get("enabled"):
            continue
        keyword = str(entry.get("keyword") or "").strip()
        if not keyword:
            continue
        normalized_keyword = _normalize_for_match(keyword)
        if not normalized_keyword:
            continue
        # المساواة الكاملة (==) وليس الاحتواء — Exact Match بالظبط كما طلب المدير
        if normalized_message == normalized_keyword:
            return entry
    return None


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
            # استخدام توقيت القاهرة (UTC+3) كما يخزنه النظام كله — لا نستخدم utcnow أبداً
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


def _send_one_message(agent, source: str, sender_identifier: str, location: str,
                      receiving_phone_id, text: str) -> tuple:
    """إرسال رسالة نصية واحدة عبر القناة الصحيحة (واتساب أو فيسبوك)."""
    try:
        if str(source).lower() == "whatsapp" or str(sender_identifier).startswith("20"):
            return agent.send_whatsapp_message(
                sender_identifier,
                text=text,
                location=location,
                receiving_phone_id=receiving_phone_id,
            )
        return agent.send_facebook_message(sender_identifier, text=text)
    except Exception as e:
        log.error(f"Send error: {e}")
        return False, str(e)


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
    # تمت إضافة هذا الشرط لتطبيق قاعدة النظام 15: الفلترة الصفرية الصارمة —
    # العملاء الذين يسألون عن أسعار برامج الحج هم من عملاء القسم الديني فقط،
    # وأي قسم آخر (Hurghada/Sharm/Sales/Drivers) لا يدخل ضمن هذا الرد إطلاقاً.
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

    # ===== البحث عن الكلمة المفتاحية الدقيقة (Exact Match) =====
    matched = _match_keyword(message_body)
    if not matched:
        # لا توجد كلمة مطابقة → يترك النظام الأساسي (AI) يتعامل مع الرسالة
        return {"ok": True, "skipped": "no_keyword_match", "chat_id": chat_id}

    reply_parts = matched.get("reply_parts") or []
    # تنظيف: نص حرفي واحد فقط إن لم يكن مصفوفة (توافق مع الصيغة القديمة)
    if isinstance(reply_parts, str):
        reply_parts = [reply_parts]
    reply_parts = [str(p).strip() for p in reply_parts if str(p).strip()]
    if not reply_parts:
        return {"ok": True, "skipped": "empty_reply", "chat_id": chat_id}

    # ===== منع التكرار (الحجز الذري) - بعد تحديد الكلمة وقبل الإرسال =====
    # الـ claim يعتمد على مفتاح موحد (chat_id + hash النص المطبع) وليس على
    # mid المتغير من فيسبوك، حتى لو وصلت نفس الرسالة أكثر من مرة خلال النافذة
    # الزمنية. كما يتجاهل الإيموجي والنقاط في النص لمنع التكرار.
    # الـ claim الواحد يغطي الرسالتين معاً (حزمة واحدة) — يمنع إرسال نصف الرد
    # ثم إعادة إرسال النصف الثاني لو وصلت الرسالة مكررة.
    claimed = _claim_reply(chat_id, incoming_external_message_id, message_body, matched.get("keyword"))
    if not claimed:
        return {"ok": True, "skipped": "already_processed", "chat_id": chat_id}

    # ===== الإرسال الفوري عبر القناة الصحيحة (رسالتين متتاليتين ورا بعض) =====
    channel = source if source else "Facebook"
    sent_parts = 0
    errors = []
    for idx, part in enumerate(reply_parts):
        ok, error = _send_one_message(
            agent, source, sender_identifier, location, receiving_phone_id, part
        )
        if not ok:
            errors.append({"part": idx + 1, "error": str(error)[:300]})
            log.warning(f"Send failed for chat {chat_id} part {idx + 1}: {error}")
            break
        sent_parts += 1
        # تسجيل كل رسالة في سجل المحادثة فور نجاحها
        try:
            import chat_db
            chat_db.add_message(
                chat_id=chat_id,
                sender_type="agent",
                text=part,
                status="sent",
                source=channel,
            )
        except Exception as e:
            log.warning(f"Failed to log reply part {idx + 1}: {e}")
        # فاصل قصير بين الرسالتين (رسالتين متقطعتين ورا بعض كما طلب المدير)
        if idx < len(reply_parts) - 1 and INTER_MESSAGE_DELAY_SECONDS > 0:
            time.sleep(INTER_MESSAGE_DELAY_SECONDS)

    if sent_parts == 0:
        # فشلت الرسالة الأولى نفسها → نعتبر الإرسال فاشلاً
        return {
            "ok": False,
            "skipped": "send_failed",
            "chat_id": chat_id,
            "keyword": matched.get("keyword"),
            "sent_parts": 0,
            "errors": errors,
        }

    # ===== إنهاء الحالة بعد نجاح الإرسال (مسح المسودات وإلغاء مسار AI) =====
    try:
        import chat_db
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
                    reason="religious_all_prices_autoreply",
                )
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Failed to finalize reply state: {e}")

    return {
        "ok": True,
        "sent": True,
        "chat_id": chat_id,
        "keyword": matched.get("keyword"),
        "channel": channel,
        "sent_parts": sent_parts,
        "total_parts": len(reply_parts),
        "partial_error": errors[0] if errors else None,
        "reply_preview": reply_parts[0][:120],
    }
