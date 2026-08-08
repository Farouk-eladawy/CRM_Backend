# -*- coding: utf-8 -*-
"""
Workflow: Religious Umrah 8-Day Follow-Up - ديني (عمرة ٨ أيام - إعلان 120248067160660757)
=========================================================================================
نظام المتابعة التلقائية (Follow-Up) لبرنامج "عمرة الـ٨ أيام" على فيسبوك ماسنجر
داخل نافذة الـ ٢٤ ساعة — يتابع العملاء المهتمين من الإعلان المحدد ويحوّلهم
لحجز فعلي عبر ٣ رسائل مجدولة.

شرط التفعيل (فلترة صارمة من الجذور في SQL - لا نلمس أي إعلان أو قسم آخر):
    WHERE facebook_ad_id = '120248067160660757'
    AND (is_deleted IS NULL OR is_deleted = 0)

نظام الجدولة — دورة فحص كل ٦٠ دقيقة (مُسجَّلة في automation_workflows):
    - المتابعة ١: مرّ من ساعة إلى ٣ ساعات على آخر رسالة من العميل
      (وليس آخر رسالة منّا — قاعدة المدير صراحةً) → تُرسل الرسالة ١ إن لم تُرسل.
    - المتابعة ٢: مرّ من ٦ إلى ٩ ساعات على آخر رسالة من العميل
      → تُرسل الرسالة ٢ إن لم تُرسل.
    - المتابعة ٣: مرّ من ٢١ إلى ٢٢ ساعة على آخر رسالة من العميل
      → تُرسل الرسالة ٣ إن لم تُرسل.
    - كل رسالة تُرسل مرة واحدة فقط لكل محادثة (سجل حالة: أُرسلت/لم تُرسل).
    - إذا ردّ العميل بأي رسالة في أي وقت → أوقف التسلسل فوراً وأعد ضبط العدّاد
      من الصفر (رده الجديد = بداية نافذة جديدة، والرسائل الثلاث تعود متاحة).
    - لا ترسل أي رسالة بعد مرور ٢٣ ساعة من آخر رسالة للعميل (نافذة ميتا ٢٤ ساعة).

شروط الإيقاف النهائي (Stop Conditions):
    1) العميل أرسل رقم موبايل (يبدأ بـ 01 ويتكون من 11 رقماً) → وسم
       «Lead جاهز للاتصال» (Tag) + حفظ الرقم في customer_phone + إشعار فوري
       للفريق البشري (needs_help=1 + System Log) + إيقاف التسلسل نهائياً.
       (لا نرسل أي رد للعميل عند استلام الرقم — الفريق البشري يتواصل معه.)
    2) العميل أكّد الحجز أو حوّل العربون → تحويل لمسار الحجز
       (needs_help=1 + System Log) + إيقاف نهائي.
    3) العميل رفض صراحة أو طلب عدم التواصل → إيقاف نهائي + تسجيل الـ sender
       في سجل الإيقاف الدائم (لا نرسل له في محادثات جديدة من نفس الإعلان).
    4) تدخّل موظف بشري (needs_help=1 أو is_closed=1) → إيقاف السلسلة.

الكلمة المفتاحية «موعد»:
    - إذا أرسل العميل كلمة «موعد» (أو مواعيد/الميعاد) → أرسل له مواعيد السفر
      المتاحة وخطوات الحجز + أعد ضبط العدّاد (الرسائل الثلاث تعود متاحة).

ملاحظات هندسية (لماذا هذه الشروط):
    - التوقيت: نستخدم chat_db.get_cairo_time() (توقيت القاهرة UTC+3) كما يفعل
      النظام بالكامل، ولا نستخدم datetime.now(timezone.utc) إطلاقاً (قاعدة F).
    - الحالة: يُمنع استخدام agent.load_state/save_state (غير موجودة في
      run_script)، لذا نستخدم ملف JSON محلي عبر fts_paths.get_data_path
      (قاعدة النظام G) لمنع التكرار وإعادة الإرسال.
    - نصوص الرسائل الثلاث تُرسل كما هي بالحرف (لا تعديل ولا إضافة — قاعدة المدير).
    - تحسين الأداء: نفلتر المحادثات من الجذور في SQL (facebook_ad_id + نافذة
      زمنية 25 ساعة على last_message_time) بدلاً من جلب كل المحادثات وفلترتها
      برمجياً (قاعدة النظام 10-7).
    - حد أقصى للإرسال في كل تشغيل (MAX_SENDS_PER_RUN) حتى لا تتجاوز مدة
      التشغيل timeout الـ http_request (60 ثانية) — التشغيل التالي يكمل الباقي
      لأن الحالة محفوظة فور كل إرسال.
"""

import os
import json
import re
import sqlite3
import logging
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ثوابت السير العمل
# =============================================================================
# الإعلان المستهدف فقط (شرط التفعيل الحصري — Ad ID من طلب المدير)
TARGET_AD_ID = "120248067160660757"

# قاعدة بيانات المحادثات (نفس مسار chat_db)
DB_FILE = get_data_path("chat_history.db")

# ملف الحالة المحلي (قاعدة النظام G: يُمنع agent.load_state)
STATE_FILE = get_data_path("religious_umrah_8day_followup_state.json")

# عتبات التوقيت (حسب جدول المدير حرفياً — الوقت يُحسب من آخر رسالة من العميل)
STAGE1_MIN_HOURS = 1.0            # المتابعة 1: من 1 إلى 3 ساعات
STAGE1_MAX_HOURS = 3.0
STAGE2_MIN_HOURS = 6.0            # المتابعة 2: من 6 إلى 9 ساعات
STAGE2_MAX_HOURS = 9.0
STAGE3_MIN_HOURS = 21.0           # المتابعة 3: من 21 إلى 22 ساعة
STAGE3_MAX_HOURS = 22.0
WINDOW_HARD_STOP_HOURS = 23.0     # لا إرسال بعد 23 ساعة من آخر رسالة عميل

# حد أقصى للإرسال في كل تشغيل (حتى لا يتجاوز timeout الـ http_request)
MAX_SENDS_PER_RUN = 20

log = logging.getLogger("ReligiousUmrah8DayFollowup")

# =============================================================================
# نصوص الرسائل (كما هي بالحرف من برومبت المدير — لا تغيير ولا إعادة صياغة)
# =============================================================================
# 🟢 الرسالة رقم 1 (قيمة بدون طلب) — بعد 1 إلى 3 ساعات
MSG_STAGE1 = (
    "معلومة تهمك 🧡 برنامج الـ٨ أيام ده أوفر برامجنا لإن فندق منازل العين قريب "
    "من الحرم — حوالي ٥ دقايق بالباص والباصات شغالة على مدار اليوم. يعني بتصلي "
    "في الحرم براحتك من غير ما تدفع فرق سعر فنادق الحرم. لو عندك أي سؤال اسأل "
    "براحتك 🙏"
)

# 🟡 الرسالة رقم 2 (كسر الاعتراض + طلب الرقم) — بعد 6 إلى 9 ساعات
MSG_STAGE2 = (
    "وعشان نسهّل عليك: الحجز بيبدأ بـ٥٠٪ بس والباقي قبل السفر بأسبوعين، والأوراق "
    "صورة باسبورت + صورة شخصية ✅ لو تحب حد من فريقنا يكلمك ويجاوبك على كل حاجة "
    "في مكالمة واحدة — ابعتلنا رقم الواتساب بتاعك وقولنا الوقت المناسب 📞"
)

# 🔴 الرسالة رقم 3 (آخر فرصة — اختيارين) — بعد 21 إلى 22 ساعة
MSG_STAGE3 = (
    "يا فندم، عشان نضمنلك مكان في أقرب رحلة (من ٣٤٬٧٥٠ ج) — اختار اللي يريحك:\n"
    "📩 ابعت كلمة «موعد» وهنبعتلك التواريخ المتاحة هنا في الشات\n"
    "☎️ أو سيب رقمك ومسؤول الحجز هيكلمك من غير أي التزام\n"
    "احنا معاك في الحالتين 🧡"
)

# 📅 رد الكلمة المفتاحية «موعد»: مواعيد السفر المتاحة + خطوات الحجز
# (مبنية على بيانات النظام الفعلية: المواعيد ٢ سبتمبر / ٢٣ سبتمبر / ١٤ أكتوبر
# وخطوات الحجز من نص الرسالة ٢ نفسها — ٥٠٪ عربون + أوراق بسيطة)
MSG_DATES_REPLY = (
    "أهلًا بحضرتك 🕋 مواعيد السفر المتاحة لبرنامج عمرة الـ٨ أيام:\n"
    "🗓 ٢ سبتمبر\n"
    "🗓 ٢٣ سبتمبر\n"
    "🗓 ١٤ أكتوبر\n\n"
    "خطوات الحجز بسيطة:\n"
    "✅ الحجز بيبدأ بـ٥٠٪ والباقي قبل السفر بأسبوعين\n"
    "✅ الأوراق: صورة باسبورت + صورة شخصية\n\n"
    "لو تحب تحجز على أي موعد، قولنا ونساعدك في كل خطوة 🧡"
)

# وسم العميل الجاهز للاتصال (Tag باسم ثابت — قاعدة المدير)
LEAD_READY_TAG = "Lead جاهز للاتصال"

# =============================================================================
# أدوات التوقيت (توقيت القاهرة فقط — قاعدة النظام F)
# =============================================================================
def _now():
    """الوقت الحالي بتوقيت القاهرة (UTC+3) بدون tzinfo لسهولة الطرح."""
    try:
        import chat_db
        now = datetime.fromisoformat(chat_db.get_cairo_time())
    except Exception:
        now = datetime.utcnow() + timedelta(hours=3)
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    return now


def _parse_dt(value):
    """تحويل أي صيغة تاريخ في قاعدة البيانات إلى datetime (بدون tzinfo)."""
    if not value:
        return None
    try:
        s = str(value)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        d = datetime.fromisoformat(s)
    except Exception:
        try:
            d = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None
    if d.tzinfo is not None:
        d = d.replace(tzinfo=None)
    return d


# =============================================================================
# أدوات الحالة المحلية (قاعدة النظام G - ملف JSON عبر fts_paths)
# =============================================================================
def _load_state() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if isinstance(data, dict):
                data.setdefault("chats", {})
                data.setdefault("opted_out_senders", {})
                return data
            return {"chats": {}, "opted_out_senders": {}}
    except Exception as e:
        log.error(f"Failed to load state: {e}")
    return {"chats": {}, "opted_out_senders": {}}


def _save_state(state: dict):
    """حفظ فوري بعد كل حدث مهم حتى لا نكرر الإرسال لو توقف التشغيل فجأة."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except Exception as e:
        log.error(f"Failed to save state: {e}")


# =============================================================================
# أدوات النصوص والتطبيع
# =============================================================================
_AR_TRANS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي"})
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _normalize_keyword(text: str) -> str:
    """تطبيع النص للمطابقة فقط (وليس للتغيير في الرسائل):
    توحيد الهمزات، إزالة التشكيل والتطويل، تحويل الأرقام العربية إلى لاتينية،
    وإزالة الإيموجي وعلامات الترقيم — حتى نلتقط كتابة العميل بأي صيغة.
    """
    s = str(text or "").strip().lower()
    s = re.sub(r"[\u064B-\u065F\u0640]", "", s)
    s = s.translate(_AR_TRANS).translate(_AR_DIGITS).translate(_FA_DIGITS)
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


# رسائل النظام/الإحالة التي ليست تفاعلاً حقيقياً (تُستبعد من حساب الوقت)
_SYSTEM_PREFIXES = (
    "[facebook ad referral]",
    "[facebook referral]",
    "[system log]",
    "[system]",
    "[proposed_draft]",
    "[auto",
)


def _is_system_noise(text: str, sender_type: str = "") -> bool:
    """رسائل النظام والإحالة والمقترحات غير الجاهزة — ليست تفاعلاً حقيقياً
    ولا تُحتسب في توقيت المتابعات (لا من العميل ولا منّا).
    """
    t = str(text or "").strip()
    if not t:
        return True
    low = t.lower()
    for p in _SYSTEM_PREFIXES:
        if low.startswith(p):
            return True
    return False


# رسائل الميديا غير النصية (صوت/فيديو/ستيكر/صورة...) — تفاعل حقيقي من العميل
# يُحتسب في التوقيت لكن لا يُفحص للكلمات المفتاحية (لا يحتوي كلاماً مكتوباً)
_MEDIA_PREFIXES = (
    "[customer sent an audio",
    "[customer sent a video",
    "[customer sent a sticker",
    "[customer sent a document",
    "[customer sent a message of type",
    "[customer shared a location",
    "[customer shared contacts",
    "[customer sent a photo",
    "[customer sent an image",
    "[customer sent a picture",
    "[customer sent a voice",
    "[customer sent media",
)


def _is_media_placeholder(text: str) -> bool:
    low = str(text or "").strip().lower()
    return any(low.startswith(p) for p in _MEDIA_PREFIXES)


def _is_real_customer_message(text: str, sender_type: str) -> bool:
    """رسالة عميل حقيقية (نصية أو ميديا) تُبقي السلسلة/النافذة حية."""
    if str(sender_type or "").strip().lower() != "customer":
        return False
    return not _is_system_noise(text, sender_type)


# =============================================================================
# كشف نوايا رسائل العميل (رقم / حجز / إيقاف / موعد / رد عادي)
# =============================================================================
_OPTOUT_PATTERNS = (
    r"متبعتليش", r"متبعتلوش", r"متكلمنيش", r"متكلمناش", r"متزعجنيش",
    r"بلاش تبعت", r"بلاش رسا[يئ]ل", r"مش عايز رسا[يئ]ل", r"مش عايز اتصالات",
    r"مش مهتم", r"اوقفوا", r"اوقفو", r"وقفو", r"لا ترسل", r"لا تبعث",
    r"شيلني", r"انزعني", r"ممنوع ترسل", r"مش هحجز", r"مش ححجز",
    r"\bstop\b", r"\bunsubscribe\b", r"don'?t contact", r"no more messages",
    r"leave me alone", r"مكفيني", r"انتو ضايقيني", r"ضايقني",
)


def _is_optout(text: str) -> bool:
    """كشف طلب العميل إيقاف التواصل نهائياً (لا نرسل له مجدداً أبداً)."""
    norm = _normalize_keyword(text)
    for p in _OPTOUT_PATTERNS:
        if re.search(p, norm):
            return True
    return False


def _extract_phone(text: str):
    """استخراج رقم موبايل مصري (يبدأ بـ 01 ويتكون من 11 رقماً — قاعدة المدير):
    يقبل الصيغ: 01012345678 / 20 10 1234 5678 / 002010... / +2010... /
    أرقام عربية ٠١٠١٢٣٤٥٦٧٨. يعيد الرقم موحّداً (11 رقماً يبدأ بـ 01) أو None.
    """
    s = _normalize_keyword(text)
    s = re.sub(r"[\s\-\.\(\)]", "", s)
    # بادئات اختيارية: 002 / 20 — ثم 0?1[0125] متبوعاً بـ 8 أرقام
    m = re.search(r"(?<!\d)(?:002|20)?0?1[0125][0-9]{8}(?!\d)", s)
    if not m:
        return None
    digits = m.group(0)
    if digits.startswith("002"):
        digits = digits[3:]
    elif digits.startswith("20") and len(digits) >= 12:
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("1"):
        digits = "0" + digits
    if len(digits) == 11 and digits.startswith("01"):
        return digits
    return None


# أنماط تأكيد الحجز / تحويل العربون (شرط الإيقاف 2)
_BOOKING_PATTERNS = (
    r"اكد الحجز", r"اكدت الحجز", r"تاكيد الحجز", r"تأكيد الحجز",
    r"تم الحجز", r"تم تاكيد", r"حجزت", r"حجزنا", r"اتاكد الحجز",
    r"عربون", r"حولت العربون", r"حولت عربون", r"دفعت العربون", r"دفع العربون",
    r"حوالة", r"حوالت العربون", r"تم الدفع", r"تم التحويل",
    r"دفعت المبلغ", r"حولت المبلغ", r"حولت الفلوس", r"دفعت الفلوس",
    r"\bbook(?:ed|ing)?\b", r"\bpaid\b", r"\bdeposit\b",
)


def _is_booking_intent(text: str) -> bool:
    """كشف تأكيد الحجز أو تحويل العربون (شرط الإيقاف 2)."""
    norm = _normalize_keyword(text)
    for p in _BOOKING_PATTERNS:
        if re.search(p, norm):
            return True
    return False


# الكلمة المفتاحية «موعد» — طلب مواعيد السفر المتاحة
_DATES_PATTERNS = (
    r"موعد", r"مواعيد", r"الميعاد", r"معاد",
)


def _is_dates_request(text: str) -> bool:
    """كشف طلب العميل لمواعيد السفر (كلمة «موعد» أو مواعيد/الميعاد)."""
    norm = _normalize_keyword(text)
    for p in _DATES_PATTERNS:
        if re.search(p, norm):
            return True
    return False


def _classify_customer_message(text: str):
    """تصنيف رسالة العميل الواردة:
    يعيد (category, phone) حيث category ∈ {opt_out, phone, booking, dates, reply}.
    - opt_out: طلب إيقاف التواصل نهائياً.
    - phone:   تحتوي رقم موبايل (01 + 11 رقماً).
    - booking: تأكيد حجز أو تحويل عربون.
    - dates:   كلمة «موعد» (طلب مواعيد السفر).
    - reply:   أي رد آخر (المساعد الأساسي يتعامل معه — يُعاد ضبط العدّاد).
    """
    if _is_optout(text):
        return "opt_out", None
    phone = _extract_phone(text)
    if phone:
        return "phone", phone
    if _is_booking_intent(text):
        return "booking", None
    if _is_dates_request(text):
        return "dates", None
    return "reply", None


# =============================================================================
# استعلامات قاعدة البيانات (فلترة صارمة من الجذور — قاعدة النظام 10-7)
# =============================================================================
def _get_ad_conversations(cursor, now: datetime):
    """المحادثات الواردة من الإعلان المستهدف فقط.
    الفلترة تتم في SQL من الجذور:
      - facebook_ad_id = TARGET_AD_ID (شرط التفعيل الحصري)
      - last_message_time حديثة (خلال 25 ساعة) — أي محادثة أقدم من ذلك تكون
        نافذة الـ 24 ساعة مغلقة ولا يمكن مراسلتها أصلاً، فلا داعي لجلبها
        (تحسين الأداء بدلاً من جلب كل المحادثات وفلترتها برمجياً).
      - نرتب الأقدم أولاً (ASC) بحيث تُعالج المحادثات الأقرب لإغلاق نافذة
        مراحلها قبل الأحدث فلا تُحرم رسالة M3 بسبب MAX_SENDS_PER_RUN.
    """
    cutoff = (now - timedelta(hours=WINDOW_HARD_STOP_HOURS + 2)).isoformat()
    cursor.execute(
        """
        SELECT chat_id, sender_identifier, contact_name, source, location,
               receiving_phone_id, last_message_time, needs_help, is_closed,
               auto_reply_hold_until, customer_phone
        FROM conversations
        WHERE facebook_ad_id = ?
          AND (is_deleted IS NULL OR is_deleted = 0)
          AND last_message_time IS NOT NULL
          AND last_message_time >= ?
        ORDER BY last_message_time ASC
        """,
        (TARGET_AD_ID, cutoff),
    )
    rows = cursor.fetchall()
    return [dict(r) for r in rows] if rows else []


def _last_real_customer_message(cursor, chat_id):
    """آخر رسالة حقيقية من العميل — مرساة نافذة الـ 24 ساعة وكل المراحل.
    نستبعد رسائل النظام/الإحالة ([Facebook Ad Referral]، [System Log]،
    [PROPOSED_DRAFT]...). رسائل الميديا من العميل (صوت/فيديو/ستيكر) هي تفاعل
    حقيقي يُحتسب في التوقيت لكن لا يُفحص نصها للكلمات المفتاحية.
    يعيد (text, timestamp) أو (None, None).
    """
    cursor.execute(
        """
        SELECT text, timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        ORDER BY timestamp DESC
        LIMIT 30
        """,
        (chat_id,),
    )
    for row in cursor.fetchall():
        text = str(row[0] or "")
        if _is_system_noise(text, "customer"):
            continue
        return text, row[1]
    return None, None


def _stage_already_sent_in_db(cursor, chat_id: str, msg_text: str) -> bool:
    """حماية ذاتية ضد الإرسال المكرر (Self-Healing): يفحص سجل المحادثة في
    قاعدة البيانات — هل أُرسلت هذه الرسالة (من أي نسخة سابقة من الـ Workflow
    أو حتى من المساعد الأساسي) لهذه المحادثة من قبل؟
    السبب: لو فُقد ملف الحالة أو أُعيد ضبطه (كما حدث عند ترقية صيغة الحالة)،
    نمنع إرسال رسالة سبق ووصلت للعميل فعلاً — لا تكرار أبداً مهما كانت الظروف.
    ملاحظة: تُقارَن النصوص بعد توحيد المسافات والأسطر (collapse whitespace)
    لأن بعض النسخ السابقة خزّنت الرسالة بفواصل أسطر أو مسافات مختلفة.
    """
    if not msg_text:
        return True
    try:
        def _norm(s):
            return re.sub(r"\s+", " ", str(s or "").strip())
        needle = _norm(msg_text)
        cursor.execute(
            """
            SELECT text FROM messages
            WHERE chat_id = ? AND sender_type IN ('agent', 'ai')
            ORDER BY timestamp DESC LIMIT 50
            """,
            (chat_id,),
        )
        for row in cursor.fetchall():
            if _norm(row[0]) == needle:
                return True
        return False
    except Exception as e:
        log.warning(f"Failed to check already-sent stage for {chat_id}: {e}")
        return False


def _hold_active(hold_until, now: datetime) -> bool:
    """هل فترة إيقاف الرد الآلي (auto_reply_hold_until) ما زالت سارية؟
    (تأجيل مؤقت فقط — لا يُعد تدخلاً بشرياً دائماً).
    """
    if not hold_until:
        return False
    d = _parse_dt(hold_until)
    return bool(d and d > now)


# =============================================================================
# الإرسال والتحويل والإشعارات
# =============================================================================
def _send_message(agent, conv: dict, text: str, dry_run: bool = False):
    """إرسال الرسالة عبر القناة الصحيحة (Facebook / WhatsApp) وتسجيلها في سجل المحادثة."""
    if dry_run:
        return True, None
    source = str(conv.get("source") or "").strip().lower()
    sender_id = str(conv.get("sender_identifier") or "").strip()
    chat_id = str(conv.get("chat_id") or "").strip()
    if not sender_id or not chat_id:
        return False, "missing_sender_or_chat"
    try:
        # القناة تُحدَّد من عمود source أساساً (أدق وأأمن من تخمين المعرفات)
        is_wa = source == "whatsapp" or (not source and sender_id.startswith("20") and len(sender_id) > 10)
        if is_wa:
            channel = "WhatsApp"
            ok, resp = agent.send_whatsapp_message(
                sender_id,
                text=text,
                location=str(conv.get("location") or "Unknown"),
                receiving_phone_id=str(conv.get("receiving_phone_id") or "").strip() or None,
            )
        else:
            channel = "Facebook"
            ok, resp = agent.send_facebook_message(sender_id, text=text)
        if not ok:
            return False, str(resp or "")[:300]
        try:
            import chat_db
            chat_db.add_message(chat_id=chat_id, sender_type="agent", text=text, status="sent", source=channel)
            try:
                chat_db.mark_conversation_read(chat_id)
            except Exception:
                pass
        except Exception as e:
            log.warning(f"Failed to log sent message for {chat_id}: {e}")
        return True, None
    except Exception as e:
        return False, str(e)[:300]


def _tag_chat(chat_id: str, tag: str, now_iso: str, dry_run: bool = False):
    """إضافة وسم (Tag) للمحادثة في sales_customer_state.tags (إضافة فقط —
    لا حذف لأي وسم أو حقل موجود، احتراماً لقاعدة النظام 8).
    """
    if dry_run:
        return
    try:
        conn = sqlite3.connect(DB_FILE, timeout=15.0)
        c = conn.cursor()
        c.execute("SELECT tags FROM sales_customer_state WHERE chat_id = ?", (chat_id,))
        row = c.fetchone()
        tags = []
        if row and row[0]:
            try:
                tags = json.loads(str(row[0]))
                if not isinstance(tags, list):
                    tags = []
            except Exception:
                tags = []
        if tag not in tags:
            tags.append(tag)
        c.execute(
            """
            INSERT INTO sales_customer_state (chat_id, tags, updated_at, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                tags = excluded.tags,
                updated_at = excluded.updated_at
            """,
            (chat_id, json.dumps(tags, ensure_ascii=False), now_iso, now_iso),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning(f"Failed to tag chat {chat_id} with '{tag}': {e}")


def _save_phone_and_notify(chat_id: str, phone: str, now_iso: str, dry_run: bool = False):
    """شرط الإيقاف 1: تسجيل الرقم في بيانات العميل (customer_phone) +
    وسم «Lead جاهز للاتصال» + إشعار فوري للفريق البشري:
    needs_help=1 (يُظهر المحادثة للموظف البشري في لوحة التحكم) + System Log.
    ملاحظة: لا نرسل أي رسالة رد للعميل عند استلام الرقم — الفريق البشري/
    المساعد الأساسي هو من يتواصل معه مباشرة.
    """
    if dry_run:
        return
    try:
        import chat_db
        try:
            chat_db.update_conversation_info(chat_id, customer_phone=phone)
        except Exception as e:
            log.warning(f"Failed to save customer_phone for {chat_id}: {e}")
        try:
            chat_db.update_conversation_info(chat_id, needs_help=True)
        except Exception as e:
            log.warning(f"Failed to set needs_help for {chat_id}: {e}")
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Umrah 8-day follow-up: customer phone received ({phone}) - وسم: {LEAD_READY_TAG} - notify human team",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to save/notify phone for {chat_id}: {e}")
    _tag_chat(chat_id, LEAD_READY_TAG, now_iso, dry_run)


def _transfer_to_booking(chat_id: str, reason: str, now_iso: str, dry_run: bool = False):
    """شرط الإيقاف 2: تحويل المحادثة لمسار الحجز (إشعار للفريق البشري) +
    إيقاف السلسلة.
    """
    if dry_run:
        return
    try:
        import chat_db
        try:
            chat_db.update_conversation_info(chat_id, needs_help=True)
        except Exception as e:
            log.warning(f"Failed to set needs_help for {chat_id}: {e}")
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Umrah 8-day follow-up: transferred to booking path ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to transfer {chat_id}: {e}")


def _log_stop_reason(chat_id: str, reason: str, dry_run: bool = False):
    """تسجيل سبب إيقاف السلسلة في سجل المحادثة (أثر توثيقي فقط — لا رسالة للعميل)."""
    if dry_run:
        return
    try:
        import chat_db
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Umrah 8-day follow-up: chain stopped ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to log stop reason for {chat_id}: {e}")


# =============================================================================
# منطق الحالة ومعالجة الردود
# =============================================================================
def _init_entry(conv: dict, last_customer_ts: datetime, last_customer_text: str,
                now_iso: str) -> dict:
    """تهيئة سجل الحالة لمحادثة جديدة (العدّاد من الصفر)."""
    return {
        "last_customer_reply": last_customer_ts.isoformat(),
        "stage1_sent": False,
        "stage2_sent": False,
        "stage3_sent": False,
        "stopped": False,
        "stop_reason": "",
        "opted_out": False,
        "sender_identifier": str(conv.get("sender_identifier") or "").strip(),
        "last_customer_text": str(last_customer_text or "")[:200],
        "updated_at": now_iso,
    }


def _reset_counter(entry: dict, last_customer_ts: datetime, last_customer_text: str,
                   now_iso: str):
    """إعادة ضبط العدّاد من الصفر (رده الجديد = بداية نافذة جديدة، والرسائل
    الثلاث تعود متاحة من جديد) — قاعدة المدير.
    """
    entry["last_customer_reply"] = last_customer_ts.isoformat()
    entry["stage1_sent"] = False
    entry["stage2_sent"] = False
    entry["stage3_sent"] = False
    entry["last_customer_text"] = str(last_customer_text or "")[:200]
    entry["updated_at"] = now_iso


def _handle_stop_categories(agent, conv, entry, category, phone, now_iso, dry_run):
    """معالجة فئات الإيقاف النهائي (opt_out / phone / booking):
    يعيد (action_key, sent) حيث sent = هل أُرسلت رسالة فعلية للعميل.
    """
    chat_id = str(conv.get("chat_id") or "").strip()
    if category == "opt_out":
        # إيقاف نهائي بدون إرسال أي رسالة (العميل طلب عدم التواصل)
        entry["opted_out"] = True
        entry["stopped"] = True
        entry["stop_reason"] = "customer_opt_out"
        _log_stop_reason(chat_id, "customer_opt_out", dry_run)
        return "opt_out", False
    if category == "phone":
        _save_phone_and_notify(chat_id, phone, now_iso, dry_run)
        entry["stopped"] = True
        entry["stop_reason"] = f"phone_received:{phone}"
        return "phone", False
    if category == "booking":
        _transfer_to_booking(chat_id, "booking_confirmed_or_deposit", now_iso, dry_run)
        entry["stopped"] = True
        entry["stop_reason"] = "booking_confirmed"
        return "booking", False
    return "reply", False


def _handle_new_reply(agent, conv, entry, text, new_ts, now_iso, dry_run):
    """معالجة رد جديد من العميل أثناء السلسلة (أو أول رسالة لمحادثة جديدة):
    - opt_out → إيقاف نهائي (يُسجَّل على الـ sender ليشمل المحادثات الجديدة).
    - phone   → تسجيل الرقم + وسم «Lead جاهز للاتصال» + إشعار فريق بشري + إيقاف.
    - booking → تحويل لمسار الحجز + إيقاف.
    - dates   → إرسال مواعيد السفر المتاحة وخطوات الحجز + إعادة ضبط العدّاد
                (new_ts = وقت رسالة «موعد» = بداية النافذة الجديدة).
    - reply   → إعادة ضبط العدّاد فقط (المساعد الأساسي يرد على العميل،
                new_ts = وقت رد العميل = بداية نافذة جديدة).
    يعيد (category, sent) حيث sent=هل أُرسلت رسالة.
    """
    category, phone = _classify_customer_message(text)
    chat_id = str(conv.get("chat_id") or "").strip()

    if category in ("opt_out", "phone", "booking"):
        action_key, sent = _handle_stop_categories(agent, conv, entry, category, phone, now_iso, dry_run)
        return action_key, sent

    if category == "dates":
        # أرسل مواعيد السفر المتاحة وخطوات الحجز ثم أعد ضبط العدّاد
        ok, err = _send_message(agent, conv, MSG_DATES_REPLY, dry_run)
        _reset_counter(entry, new_ts, text, now_iso)
        return "dates", ok

    # أي رد آخر → إعادة ضبط العدّاد (الرسائل الثلاث تعود متاحة من جديد)
    _reset_counter(entry, new_ts, text, now_iso)
    return "reply", False


# =============================================================================
# منطق المراحل والجدولة
# =============================================================================
def _due_stage(entry: dict, now: datetime, last_customer_ts: datetime) -> int:
    """تحديد المرحلة المستحقة (واحدة فقط لكل محادثة في كل تشغيل):
    - المرحلة 1: لم تُرسل بعد + مرّ من 1 إلى 3 ساعات على آخر رسالة عميل.
    - المرحلة 2: لم تُرسل بعد + مرّ من 6 إلى 9 ساعات على آخر رسالة عميل.
    - المرحلة 3: لم تُرسل بعد + مرّ من 21 إلى 22 ساعة على آخر رسالة عميل.
    يعيد 0 إذا لم تكن أي مرحلة مستحقة.
    """
    elapsed = (now - last_customer_ts).total_seconds() / 3600.0

    if not entry.get("stage1_sent") and STAGE1_MIN_HOURS <= elapsed < STAGE1_MAX_HOURS:
        return 1
    if not entry.get("stage2_sent") and STAGE2_MIN_HOURS <= elapsed < STAGE2_MAX_HOURS:
        return 2
    if not entry.get("stage3_sent") and STAGE3_MIN_HOURS <= elapsed < STAGE3_MAX_HOURS:
        return 3
    return 0


def _sync_db_sent_stages(cursor, chat_id: str, entry: dict, msgs: dict) -> bool:
    """حماية ذاتية: يُدمج حالة الإرسال من قاعدة البيانات الفعلية في سجل الحالة.
    إذا كانت رسالة المرحلة (1/2/3) موجودة فعلاً في سجل المحادثة (أُرسلت من
    نسخة سابقة من الـ Workflow أو من المساعد الأساسي) نعلّمها كمرسلة فوراً
    حتى لا تتكرر أبداً حتى لو فُقد ملف الحالة أو أُعيد ضبطه.
    يعيد True إذا تطلّب ذلك حفظ الحالة.
    """
    changed = False
    for key, text in (("stage1", msgs[1]), ("stage2", msgs[2]), ("stage3", msgs[3])):
        if not entry.get(f"{key}_sent") and _stage_already_sent_in_db(cursor, chat_id, text):
            entry[f"{key}_sent"] = True
            changed = True
    return changed


# =============================================================================
# نقطة الدخول الرئيسية (يستدعيها محرك الأتمتة عبر run_script)
# =============================================================================
def run(agent, payload: dict = None) -> dict:
    """
    المعاملات (payload):
        dry_run:  (اختياري) إن كان True لا يُرسل ولا يحفظ الحالة (للاختبار فقط).
        limit:    (اختياري) عدد أقصى للمحادثات المعالجة في هذا التشغيل (للاختبار).
    """
    payload = payload or {}
    dry_run = bool(payload.get("dry_run"))
    limit = None
    try:
        limit = int(payload.get("limit") or 0) or None
    except Exception:
        limit = None

    now = _now()
    now_iso = now.isoformat()
    sent_count = 0
    errors = []
    processed_chats = 0
    actions = {"stage1": 0, "stage2": 0, "stage3": 0, "dates": 0, "opt_out": 0,
               "phone": 0, "booking": 0, "reply_reset": 0, "window_closed": 0}

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        msg = f"Failed to connect to DB: {e}"
        log.error(f"[Umrah8Day] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}

    state = _load_state()
    chats = state.setdefault("chats", {})
    opted_out_senders = state.setdefault("opted_out_senders", {})

    try:
        conversations = _get_ad_conversations(cursor, now)
        log.info(f"[Umrah8Day] Found {len(conversations)} recent conversations for ad {TARGET_AD_ID}")

        for conv in conversations:
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue
            if limit and processed_chats >= limit:
                break

            # ===== 4) تدخّل موظف بشري → إيقاف السلسلة نهائياً =====
            human_active = False
            try:
                if int(conv.get("needs_help") or 0) == 1:
                    human_active = True
            except Exception:
                pass
            try:
                if int(conv.get("is_closed") or 0) == 1:
                    human_active = True
            except Exception:
                pass
            if human_active:
                entry = chats.get(chat_id)
                if entry and not entry.get("stopped"):
                    entry["stopped"] = True
                    entry["stop_reason"] = "human_intervention"
                    entry["updated_at"] = now_iso
                    if not dry_run:
                        _save_state(state)
                continue

            # تأجيل مؤقت (auto_reply_hold_until) — نتخطى هذه الدورة فقط
            if _hold_active(conv.get("auto_reply_hold_until"), now):
                continue

            entry = chats.get(chat_id)

            # ===== مرساة الوقت: آخر رسالة حقيقية من العميل =====
            last_cust_text, last_cust_raw = _last_real_customer_message(cursor, chat_id)
            if last_cust_raw is None:
                continue
            last_cust_ts = _parse_dt(last_cust_raw)
            if last_cust_ts is None:
                continue

            sender_id = str(conv.get("sender_identifier") or "").strip()
            processed_chats += 1

            # ===== حماية ذاتية: عميل سبق وأرسل رقمه (customer_phone محفوظ) =====
            # حتى لو فُقد ملف الحالة (أو تغيّر صيغته عبر الترقية)، لا نرسل أي
            # متابعة لعميل محفوظ له رقم موبايل في قاعدة البيانات — الرقم يعني
            # أنه تحوّل لمسار «Lead جاهز للاتصال» ويجب أن يتولاه الفريق البشري
            # (قاعدة المدير: رقم موبايل → إيقاف التسلسل نهائياً).
            existing_phone = str(conv.get("customer_phone") or "").strip()
            if existing_phone:
                entry = chats.get(chat_id)
                if entry is not None and not entry.get("stopped"):
                    entry["stopped"] = True
                    entry["stop_reason"] = f"phone_already_on_record:{existing_phone}"
                    entry["updated_at"] = now_iso
                    if not dry_run:
                        _save_state(state)
                elif entry is None:
                    # لم تكن مُتتبَّعة أصلاً → نسجّل إيقافاً لمنع أي محاولة لاحقة
                    entry = _init_entry(conv, last_cust_ts, last_cust_text, now_iso)
                    entry["sender_identifier"] = sender_id
                    entry["stopped"] = True
                    entry["stop_reason"] = f"phone_already_on_record:{existing_phone}"
                    entry["updated_at"] = now_iso
                    chats[chat_id] = entry
                    if not dry_run:
                        _save_state(state)
                continue

            # ===== إيقاف محادثة قديمة قيد السلسلة لمرسل طلب الإيقاف =====
            if entry is not None and sender_id and sender_id in opted_out_senders:
                if not entry.get("stopped"):
                    entry["stopped"] = True
                    entry["stop_reason"] = "sender_opted_out"
                    entry["updated_at"] = now_iso
                    if not dry_run:
                        _save_state(state)
                continue

            # ===== محادثة جديدة: تهيئة الحالة (ثم نكمل لنفس منطق الجدولة) =====
            is_new_entry = entry is None
            if entry is None:
                # نافذة الـ 24 ساعة من آخر رسالة عميل مغلقة → لا نبدأ التتبع أصلاً
                elapsed_cust = (now - last_cust_ts).total_seconds() / 3600.0
                if elapsed_cust >= WINDOW_HARD_STOP_HOURS:
                    actions["window_closed"] = actions.get("window_closed", 0) + 1
                    continue
                # عميل سبق وطلب عدم التواصل → لا نرسل له متابعات نهائياً
                if sender_id and sender_id in opted_out_senders:
                    continue
                entry = _init_entry(conv, last_cust_ts, last_cust_text, now_iso)
                entry["sender_identifier"] = sender_id
                chats[chat_id] = entry
                if not dry_run:
                    _save_state(state)
                # أول رسالة قد تحتوي طلب إيقاف / رقم / نية حجز / موعد —
                # نعالجها فوراً (نفس منطق كشف الرد الجديد)
                if not _is_media_placeholder(last_cust_text):
                    cat, sent = _handle_new_reply(agent, conv, entry, last_cust_text, last_cust_ts, now_iso, dry_run)
                    actions[cat if cat in actions else "reply_reset"] = actions.get(cat, 0) + 1
                    if cat == "opt_out" and sender_id:
                        opted_out_senders[sender_id] = now_iso
                    entry["last_customer_text"] = str(last_cust_text or "")[:200]
                    entry["updated_at"] = now_iso
                    if sent:
                        sent_count += 1
                    if not dry_run:
                        _save_state(state)
                    if sent_count >= MAX_SENDS_PER_RUN:
                        break
                    # لو أُرسلت رسالة بالفعل في هذه الدورة (رد «موعد») → لا نرسل
                    # مرحلة في نفس التشغيل (منع رسالتين دفعة واحدة)
                    if sent:
                        continue
                    # بعد المعالجة نكمل لنفس منطق الجدولة (قد تكون المتابعة
                    # مستحقة فعلاً إن مرّ وقت كافٍ على آخر رسالة العميل)
                    # ملاحظة: إذا كان رد «reply» فقد أُعيد ضبط العدّاد والمرساة
                    # أصبحت آخر رسالة العميل — نكمل بالحساب من هذه المرساة.

            # ===== حالة نهائية: أُوقفت السلسلة → لا نعيد =====
            if entry.get("stopped"):
                continue

            # ===== كشف رد جديد من العميل أثناء السلسلة → إعادة ضبط العدّاد =====
            prev_cust_ts = _parse_dt(entry.get("last_customer_reply"))
            if (not is_new_entry) and (prev_cust_ts is None or last_cust_ts > prev_cust_ts):
                cat, sent = _handle_new_reply(agent, conv, entry, last_cust_text, last_cust_ts, now_iso, dry_run)
                actions[cat if cat in actions else "reply_reset"] = actions.get(cat, 0) + 1
                if cat == "opt_out" and sender_id:
                    opted_out_senders[sender_id] = now_iso
                entry["last_customer_text"] = str(last_cust_text or "")[:200]
                entry["updated_at"] = now_iso
                if sent:
                    sent_count += 1
                if not dry_run:
                    _save_state(state)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
                if entry.get("stopped"):
                    continue
                # لو أُرسلت رسالة بالفعل في هذه الدورة (رد «موعد») → لا نرسل
                # مرحلة في نفس التشغيل (منع رسالتين دفعة واحدة)
                if sent:
                    continue
                # بعد إعادة الضبط نكمل لنفس منطق الجدولة (المرساة = آخر رد عميل)

            # ===== لا رد جديد → منطق الجدولة الزمنية =====
            # المرساة = آخر رسالة حقيقية من العميل (وليس آخر رسالة منّا)
            last_anchor_ts = _parse_dt(entry.get("last_customer_reply")) or last_cust_ts
            elapsed_cust = (now - last_anchor_ts).total_seconds() / 3600.0

            # حماية ذاتية (Self-Healing): مزامنة حالة الإرسال من قاعدة البيانات
            # الفعلية للمحادثات الجديدة فقط (أي عندما يكون ملف الحالة مفقوداً أو
            # أُعيد ضبطه بعد ترقية الصيغة) — حتى لا تتكرر أي رسالة سبق إرسالها
            # من نسخة سابقة من الـ Workflow. أما بعد ردّ العميل وإعادة ضبط
            # العدّاد (قاعدة المدير: الرسائل الثلاث تعود متاحة من جديد) فلا
            # نمنع إعادة الإرسال — نكتفي بمزامنة المحادثات الجديدة/المفقودة.
            if is_new_entry:
                db_msgs = {1: MSG_STAGE1, 2: MSG_STAGE2, 3: MSG_STAGE3}
                try:
                    if _sync_db_sent_stages(cursor, chat_id, entry, db_msgs):
                        if not dry_run:
                            _save_state(state)
                except Exception as e:
                    log.warning(f"Failed to sync DB sent stages for {chat_id}: {e}")

            # نافذة الـ 24 ساعة انتهت (23 ساعة حد أقصى للإرسال) → لا إرسال
            if elapsed_cust >= WINDOW_HARD_STOP_HOURS:
                actions["window_closed"] = actions.get("window_closed", 0) + 1
                # حذف السجل لصغر ملف الحالة (النافذة انتهت ولا إرسال بعد)
                chats.pop(chat_id, None)
                if not dry_run:
                    _save_state(state)
                continue

            target = _due_stage(entry, now, last_anchor_ts)
            if target == 0:
                continue

            msg = {1: MSG_STAGE1, 2: MSG_STAGE2, 3: MSG_STAGE3}.get(target, "")
            if not msg:
                continue

            ok, err = _send_message(agent, conv, msg, dry_run)
            if ok:
                key = f"stage{target}"
                entry[key + "_sent"] = True
                entry["updated_at"] = now_iso
                actions[key] = actions.get(key, 0) + 1
                sent_count += 1
                if not dry_run:
                    _save_state(state)  # حفظ فوري بعد كل إرسال (منع التكرار)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
            else:
                errors.append(f"stage{target}->{chat_id}: {err}")

        message = (
            f"Ad {TARGET_AD_ID}: sent={sent_count} | processed={processed_chats} "
            f"| actions={actions} | errors={len(errors)}"
        )
        log.info(f"[Umrah8Day] {message}")
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "processed_chats": processed_chats,
            "actions": actions,
            "errors": errors[:20],
            "message": message,
        }
    except Exception as e:
        msg = f"Error in Umrah 8-day follow-up run: {e}"
        log.error(f"[Umrah8Day] {msg}")
        return {"ok": False, "sent_count": sent_count, "errors": [msg], "message": msg}
    finally:
        try:
            if not dry_run:
                _save_state(state)
            conn.close()
        except Exception:
            pass
