# -*- coding: utf-8 -*-
"""
Workflow: Religious Hajj Early-Booking Follow-Up - ديني (خصم الحجز المبكر - إعلان 120247344380410757)
======================================================================================================
نظام المتابعة التلقائية (Follow-Up) لبرنامج "حج ١٤٤٨ - خصم الحجز المبكر" على
فيسبوك ماسنجر داخل نافذة الـ ٢٤ ساعة — متابعة العملاء الواردين من إعلان محدد
بثلاث رسائل متدرجة حسب جدول القرارات الذي حدده المدير حرفياً.

شرط التفعيل (فلترة صارمة من الجذور في SQL — قاعدة النظام 15):
    WHERE facebook_ad_id = '120247344380410757'   ← هذا الإعلان فقط
    AND (is_deleted IS NULL OR is_deleted = 0)
أي محادثة من إعلان آخر أو مصدر مختلف لا تُطبق عليها هذه الأتمتة نهائياً.

جدول القرارات (كما في برومبت المدير — يُحسب الوقت من آخر رسالة من العميل
وليس آخر رسالة منّا):
    الساعات منذ آخر رسالة عميل   |  متابعات مرسلة سابقاً  |  الإجراء
    -----------------------------+------------------------+------------------------------
    أقل من 1 ساعة                |  أي عدد               |  لا ترسل شيئاً — انتظر
    من 1 إلى أقل من 6 ساعات      |  0                    |  أرسل المتابعة رقم 1
    من 6 إلى أقل من 21 ساعة      |  0 أو 1               |  أرسل المتابعة رقم 2
                                 |                       |  (لو 1 لم تُرسل أرسل 2 مباشرة)
    من 21 إلى أقل من 24 ساعة     |  0 أو 1 أو 2          |  أرسل المتابعة رقم 3 (الإغلاق)
    24 ساعة أو أكثر              |  أي عدد               |  توقف نهائياً (نافذة ميتا مقفولة)

قاعدة صارمة: رسالة متابعة واحدة كحد أقصى في الدورة الواحدة، ولا نكرر رسالة
سبق إرسالها أبداً، والحد الأقصى 3 رسائل متابعة لكل محادثة (العدّاد الكلي
لا يتجاوز 3 حتى بعد ردّ العميل — قاعدة المدير صراحةً).

شروط الإيقاف فوراً:
    1) العميل رد بأي رسالة عادية → المساعد الأساسي يرد عليه طبيعياً، ونعيد
       ضبط مرساة الساعات على آخر رسالة له، مع الإبقاء على عدد المتابعات
       المرسلة سابقاً ضمن الحد الأقصى (لا يتجاوز الإجمالي 3).
    2) العميل أرسل رقم واتساب → أرسل رسالة التأكيد المخصصة + حفظ الرقم في
       customer_phone + وسم «Lead جاهز للاتصال» + إشعار الفريق البشري
       (needs_help=1) + إيقاف نهائي.
    3) العميل أكمل الحجز أو دفع جدية الحجز → تحويل لمسار الحجز
       (needs_help=1 + System Log) + إيقاف نهائي (بدون رسالة للعميل).
    4) العميل عبّر بوضوح عن عدم الاهتمام ("مش مهتم"، "شكرًا مش عايز"،
       "بطلوا رسايل"...) → أرسل رسالة الختام المهذب + تسجيل الـ sender في
       سجل الإيقاف الدائم + إيقاف نهائي.
    5) تدخّل موظف بشري (needs_help=1 أو is_closed=1) → إيقاف نهائي.
    6) عميل محفوظ له customer_phone → إيقاف نهائي (تحوّل لمسار بشري سابقاً).

ملاحظات هندسية (لماذا هذه الشروط — قاعدة التوثيق الذاتي 13):
    - التوقيت: chat_db.get_cairo_time() (توقيت القاهرة UTC+3) فقط — ممنوع
      datetime.now(timezone.utc) (قاعدة النظام F) لتفادي أخطاء المقارنة.
    - الحالة: يُمنع agent.load_state/save_state (غير موجودة في run_script) —
      نستخدم ملف JSON محلي عبر fts_paths.get_data_path (قاعدة النظام G)
      لمنع التكرار وإعادة الإرسال، مع الحفظ الفوري بعد كل إرسال.
    - تحسين الأداء: نفلتر المحادثات من الجذور في SQL (facebook_ad_id +
      نافذة زمنية 26 ساعة على last_message_time) بدلاً من جلب كل المحادثات
      وفلترتها برمجياً (قاعدة النظام 10-7).
    - حماية ذاتية (Self-Healing): نزامن عدد المتابعات المرسلة من سجل
      المحادثة الفعلي في قاعدة البيانات (حتى لو فُقد ملف الحالة) — ولا
      نكرر أبداً رسالة سبق إرسالها.
    - حد أقصى للإرسال في كل تشغيل (MAX_SENDS_PER_RUN) حتى لا يتجاوز
      timeout الـ http_request (60 ثانية) — التشغيل التالي يكمل الباقي لأن
      الحالة تُحفظ فور كل إرسال، ونعالج الأقدم أولاً (ASC) حتى لا تفوت أي
      محادثة نافذة مراحلها.
    - لا نرسل أي رسالة بعد 24 ساعة من آخر رسالة للعميل مهما كانت الظروف
      (قيود Meta — خطأ 10).
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
# الإعلان المستهدف فقط (شرط التفعيل الحصري — Ad ID من برومبت المدير)
TARGET_AD_ID = "120247344380410757"

# قاعدة بيانات المحادثات (نفس مسار chat_db)
DB_FILE = get_data_path("chat_history.db")

# ملف الحالة المحلي (قاعدة النظام G: يُمنع agent.load_state)
STATE_FILE = get_data_path("religious_hajj_earlybooking_followup_state.json")

# عتبات جدول القرارات (حسب برومبت المدير حرفياً — الوقت من آخر رسالة عميل)
STAGE1_MIN_HOURS = 1.0    # المتابعة 1: من 1 إلى أقل من 6 ساعات
STAGE1_MAX_HOURS = 6.0
STAGE2_MIN_HOURS = 6.0    # المتابعة 2: من 6 إلى أقل من 21 ساعة
STAGE2_MAX_HOURS = 21.0
STAGE3_MIN_HOURS = 21.0   # المتابعة 3: من 21 إلى أقل من 24 ساعة
STAGE3_MAX_HOURS = 24.0
WINDOW_HARD_STOP_HOURS = 24.0   # 24 ساعة أو أكثر → توقف نهائي (نافذة ميتا)
MAX_FOLLOWUPS_TOTAL = 3         # الحد الأقصى الكلي: 3 رسائل متابعة لكل محادثة

# حد أقصى للإرسال في كل تشغيل (حتى لا يتجاوز timeout الـ http_request)
MAX_SENDS_PER_RUN = 20

log = logging.getLogger("ReligiousHajjEarlyBookingFollowup")

# =============================================================================
# نصوص الرسائل (من برومبت المدير — تُرسل كما هي بالحرف دون أي تعديل)
# =============================================================================
# 🟢 المتابعة رقم 1 — تذكير خفيف وفتح باب الأسئلة (بعد 1 إلى أقل من 6 ساعات)
MSG_STAGE1 = (
    "حضرتك لسه معانا؟ 🕋 حبيت أطمنك إن خصم الحجز المبكر لسه متاح لحضرتك كمقدم "
    "في القرعة الموسم الماضي. ولو عندك أي سؤال عن البرامج أو الفنادق أو مواعيد "
    "السداد، أنا موجود أرد على حضرتك فورًا."
)

# 🟡 المتابعة رقم 2 — الندرة وإزالة الاعتراضات (بعد 6 إلى أقل من 21 ساعة)
# (نص محدّث من المدير — 2026-08-03)
MSG_STAGE2 = (
    "عشان محدش يفوته الخصم 🧡 أماكن خصم الحجز المبكر محدودة، وبتتحجز بأسبقية "
    "جدية الحجز. للعلم، حج البري السنادي اكتمل بالفعل من كتر الإقبال، والمتاح "
    "حاليًا برنامجي حج الطيران وحج الطيران تحسين، والأماكن فيهم بتتحجز بسرعة. "
    "والمطمئن لحضرتك: جدية الحجز مستردة بالكامل لحين صدور الضوابط الرسمية "
    "— يعني بتضمن مكانك من غير أي مخاطرة. تحب أبعتلك خطوات الحجز؟"
)

# 🔴 المتابعة رقم 3 — الإغلاق ونقل التواصل لواتساب (بعد 21 إلى أقل من 24 ساعة)
# (نص محدّث من المدير — 2026-08-03: حذف رقم الهاتف المباشر)
MSG_STAGE3 = (
    "آخر رسالة مني النهارده وعدًا 🙏 لو حضرتك مهتم فعلًا ببرامج حج ١٤٤٨ "
    "والخصم، ابعتلي رقم الواتساب بتاع حضرتك وهتواصل بكل التفاصيل والعروض. "
    "ربنا يكتبلك الحج ويرزقك زيارة بيته الحرام 🕋"
)

# ✅ رسالة التأكيد عند استلام رقم واتساب (شرط الإيقاف 2)
MSG_PHONE_CONFIRM = (
    "تمام يا فندم، وصلني رقم حضرتك 🧡 هيتواصل معاك أحد زملائي على الواتساب في "
    "أقرب وقت بكل تفاصيل البرامج والخصم. شكرًا لثقة حضرتك في FTS للسياحة، "
    "وربنا يكتبلك الحج 🕋"
)

# 🤝 رسالة الختام المهذب عند عدم الاهتمام (شرط الإيقاف 4)
MSG_POLITE_CLOSE = (
    "تحت أمر حضرتك في أي وقت 🧡 ولو حبيت تسأل عن برامج الحج أو العمرة مستقبلًا، "
    "إحنا موجودين دايمًا في خدمتك. ربنا يكرمك ويرزقك زيارة بيته الحرام 🕋"
)

# قائمة الرسائل الثلاث — للفحص الذاتي (self-healing) في قاعدة البيانات
STAGE_MESSAGES = {1: MSG_STAGE1, 2: MSG_STAGE2, 3: MSG_STAGE3}

# وسم العميل الجاهز للاتصال (Tag باسم ثابت — نفس وسم سير العمل الديني الأخرى)
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
# يُحتسب في التوقيت لكن لا يُفحص نصه للكلمات المفتاحية (لا يحتوي كلاماً مكتوباً)
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
    "[facebook audio",
    "[facebook video",
    "[facebook photo",
    "[facebook image",
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
# كشف نوايا رسائل العميل (رقم / حجز / إيقاف / رد عادي)
# =============================================================================
# أنماط طلب إيقاف التواصل نهائياً — تشمل أمثلة المدير: "مش مهتم"،
# "شكرًا مش عايز"، "بطلوا رسايل"
_OPTOUT_PATTERNS = (
    r"متبعتليش", r"متبعتلوش", r"متكلمنيش", r"متكلمناش", r"متزعجنيش",
    r"بلاش تبعت", r"بلاش رسا[يئ]ل", r"مش عايز رسا[يئ]ل", r"مش عايز اتصالات",
    r"بطلوا رسا[يئ]ل", r"بطلت رسا[يئ]ل", r"اوقفوا", r"اوقفو", r"وقفو",
    r"لا ترسل", r"لا تبعث", r"شيلني", r"انزعني", r"ممنوع ترسل",
    r"مش هحجز", r"مش ححجز", r"مش مهتم", r"انا مش مهتم",
    r"شكر[ااً]?\s*مش\s*عايز", r"مش عايز الحج", r"مش عايز البرنامج",
    r"مكفيني", r"انتو ضايقيني", r"ضايقني",
    r"\bstop\b", r"\bunsubscribe\b", r"don'?t contact", r"no more messages",
    r"leave me alone",
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


# أنماط تأكيد الحجز / دفع جدية الحجز (شرط الإيقاف 3 — "أكمل الحجز أو دفع
# جدية الحجز"). لاحظ: "التسجيل المبدئي" ليس حجزاً مكتملاً فلا يُحتسب هنا.
_BOOKING_PATTERNS = (
    r"اكد الحجز", r"اكدت الحجز", r"تاكيد الحجز", r"تأكيد الحجز",
    r"تم الحجز", r"تم تاكيد", r"حجزت", r"حجزنا", r"اتاكد الحجز",
    r"عربون", r"حولت العربون", r"حولت عربون", r"دفعت العربون", r"دفع العربون",
    r"حوالة", r"حوالت العربون", r"تم الدفع", r"تم التحويل",
    r"دفعت المبلغ", r"حولت المبلغ", r"حولت الفلوس", r"دفعت الفلوس",
    r"جديه الحجز", r"دفعت الجديه", r"حولت الجديه", r"ادفع الجديه",
    r"هدفع الجديه", r"حجزت جديه", r"دفعت جديه",
    r"\bbook(?:ed|ing)?\b", r"\bpaid\b", r"\bdeposit\b",
)


def _is_booking_intent(text: str) -> bool:
    """كشف تأكيد الحجز أو دفع جدية الحجز (شرط الإيقاف 3)."""
    norm = _normalize_keyword(text)
    for p in _BOOKING_PATTERNS:
        if re.search(p, norm):
            return True
    return False


def _classify_customer_message(text: str):
    """تصنيف رسالة العميل الواردة:
    يعيد (category, phone) حيث category ∈ {opt_out, phone, booking, reply}.
    - opt_out: طلب إيقاف التواصل نهائياً (أولوية قصوى).
    - phone:   تحتوي رقم موبايل (01 + 11 رقماً).
    - booking: تأكيد حجز أو دفع جدية حجز.
    - reply:   أي رد آخر (المساعد الأساسي يرد عليه — نعيد ضبط مرساة الساعات فقط).
    """
    if _is_optout(text):
        return "opt_out", None
    phone = _extract_phone(text)
    if phone:
        return "phone", phone
    if _is_booking_intent(text):
        return "booking", None
    return "reply", None


# =============================================================================
# استعلامات قاعدة البيانات (فلترة صارمة من الجذور — قاعدة النظام 10-7 و 15)
# =============================================================================
def _get_ad_conversations(cursor, now: datetime):
    """المحادثات الواردة من الإعلان المستهدف فقط.
    الفلترة تتم في SQL من الجذور:
      - facebook_ad_id = TARGET_AD_ID (شرط التفعيل الحصري — لا نلمس أي إعلان آخر)
      - last_message_time حديثة (خلال 26 ساعة) — أي محادثة أقدم من ذلك تكون
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


def _norm_text(s: str) -> str:
    """توحيد المسافات والأسطر للمقارنة النصية فقط (لا نغير نصوص الرسائل)."""
    return re.sub(r"\s+", " ", str(s or "").strip())


def _agent_sent_texts(cursor, chat_id: str) -> set:
    """نصوص الرسائل التي أرسلها العميل/الوكيل فعلاً في هذه المحادثة (آخر 60
    رسالة) — تستخدم للحماية الذاتية ضد الإرسال المكرر.
    """
    texts = set()
    try:
        cursor.execute(
            """
            SELECT text FROM messages
            WHERE chat_id = ? AND sender_type IN ('agent', 'ai')
            ORDER BY timestamp DESC LIMIT 60
            """,
            (chat_id,),
        )
        for row in cursor.fetchall():
            if row and row[0]:
                texts.add(_norm_text(row[0]))
    except Exception as e:
        log.warning(f"Failed to read sent texts for {chat_id}: {e}")
    return texts


def _sync_sent_state(cursor, chat_id: str, entry: dict) -> bool:
    """حماية ذاتية (Self-Healing): نزامن عدد المتابعات المرسلة من سجل
    المحادثة الفعلي في قاعدة البيانات — لو فُقد ملف الحالة أو أُعيد ضبطه،
    نمنع إرسال رسالة سبق ووصلت للعميل فعلاً (لا تكرار أبداً).
    أيضاً: لو وجدنا رسالة التأكيد (رقم واتساب) أو رسالة الختام المهذب في
    السجل، نعلّم المحادثة كموقوفة (سبق إيقافها في نسخة سابقة).
    يعيد True إذا تغيّرت الحالة (يستلزم الحفظ).
    """
    changed = False
    try:
        texts = _agent_sent_texts(cursor, chat_id)
        # 1) عدد المتابعات المرسلة فعلاً من الرسائل الثلاث
        db_count = sum(1 for m in STAGE_MESSAGES.values() if _norm_text(m) in texts)
        if db_count > int(entry.get("sent_count") or 0):
            entry["sent_count"] = db_count
            changed = True
        # 2) رسالة إيقاف سبق إرسالها (تأكيد رقم / ختام مهذب) → المحادثة موقوفة
        if not entry.get("stopped") and (
            _norm_text(MSG_PHONE_CONFIRM) in texts or _norm_text(MSG_POLITE_CLOSE) in texts
        ):
            entry["stopped"] = True
            entry["stop_reason"] = "already_stopped_in_db"
            changed = True
    except Exception as e:
        log.warning(f"Failed to sync sent state for {chat_id}: {e}")
    return changed


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
    """إرسال الرسالة عبر القناة الصحيحة (Facebook / WhatsApp) وتسجيلها في سجل
    المحادثة (نفس نمط سير العمل الديني الأخرى المعتمدة).
    """
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
    """شرط الإيقاف 2 (رقم واتساب): تسجيل الرقم في customer_phone +
    وسم «Lead جاهز للاتصال» + إشعار فوري للفريق البشري:
    needs_help=1 (يُظهر المحادثة للموظف البشري في لوحة التحكم) + System Log.
    ملاحظة: رسالة التأكيد للعميل تُرسل من دالة المعالجة (نص مخصص من المدير).
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
            f"[System Log] Hajj early-booking follow-up: customer phone received ({phone}) - وسم: {LEAD_READY_TAG} - notify human team",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to save/notify phone for {chat_id}: {e}")
    _tag_chat(chat_id, LEAD_READY_TAG, now_iso, dry_run)


def _transfer_to_booking(chat_id: str, reason: str, now_iso: str, dry_run: bool = False):
    """شرط الإيقاف 3 (أكمل الحجز أو دفع جدية الحجز): تحويل المحادثة لمسار
    الحجز (إشعار للفريق البشري) + إيقاف السلسلة — بدون أي رسالة للعميل
    (الفريق البشري / المساعد الأساسي هو من يتابع معه).
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
            f"[System Log] Hajj early-booking follow-up: transferred to booking path ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to transfer {chat_id}: {e}")


def _log_stop_reason(chat_id: str, reason: str, dry_run: bool = False):
    """تسجيل سبب إيقاف السلسلة في سجل المحادثة (أثر توثيقي فقط)."""
    if dry_run:
        return
    try:
        import chat_db
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Hajj early-booking follow-up: chain stopped ({reason})",
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
    """تهيئة سجل الحالة لمحادثة جديدة: مرساة = آخر رسالة عميل، وعدد المتابعات
    المرسلة = 0 (الحد الأقصى الكلي 3 لا يُتجاوز أبداً — قاعدة المدير).
    """
    return {
        "last_customer_reply": last_customer_ts.isoformat(),
        "sent_count": 0,
        "stopped": False,
        "stop_reason": "",
        "opted_out": False,
        "sender_identifier": str(conv.get("sender_identifier") or "").strip(),
        "last_customer_text": str(last_customer_text or "")[:200],
        "updated_at": now_iso,
    }


def _reset_anchor(entry: dict, new_ts: datetime, text: str, now_iso: str):
    """إعادة ضبط مرساة الساعات فقط (رد عميل جديد = بداية نافذة جديدة).
    ملاحظة: عدد المتابعات المرسلة (sent_count) لا يُصفَّر — بل يُحتسب ضمن
    الحد الأقصى الكلي 3 (قاعدة المدير: "تُحتسب رسائل المتابعة السابقة ضمن
    الحد الأقصى — لا يتجاوز الإجمالي 3 رسائل متابعة").
    لو كانت المحادثة موقوفة بسبب إغلاق النافذة (window_closed)، رسالة العميل
    الجديدة تفتح نافذة جديدة (Meta يسمح بالرد خلال 24 ساعة من آخر رسالة
    عميل) فنزيل علامة الإيقاف مع الإبقاء على العدّاد الكلي.
    """
    entry["last_customer_reply"] = new_ts.isoformat()
    entry["last_customer_text"] = str(text or "")[:200]
    entry["updated_at"] = now_iso
    if entry.get("stop_reason") == "window_closed":
        entry["stopped"] = False
        entry["stop_reason"] = ""


def _handle_new_message(agent, conv: dict, entry: dict, text: str, new_ts: datetime,
                        now_iso: str, dry_run: bool) -> tuple:
    """معالجة رسالة جديدة من العميل (أول رسالة لمحادثة جديدة أو رد أثناء
    السلسلة) حسب شروط الإيقاف الأربعة للمدير:
    - opt_out → رسالة الختام المهذب + إيقاف نهائي (+ تسجيل الـ sender).
    - phone   → رسالة التأكيد المخصصة + حفظ الرقم + إشعار الفريق + إيقاف نهائي.
    - booking → تحويل لمسار الحجز + إيقاف نهائي (بدون رسالة للعميل).
    - reply   → إعادة ضبط مرساة الساعات فقط (لا رسالة — المساعد الأساسي يرد).
    يعيد (category, sent) حيث sent = هل أُرسلت رسالة فعلية للعميل في هذه الدورة.
    """
    category, phone = _classify_customer_message(text)
    chat_id = str(conv.get("chat_id") or "").strip()

    if category == "opt_out":
        # شرط الإيقاف 4: عدم الاهتمام الواضح → رسالة ختام مهذبة + إيقاف نهائي
        ok, err = _send_message(agent, conv, MSG_POLITE_CLOSE, dry_run)
        entry["opted_out"] = True
        entry["stopped"] = True
        entry["stop_reason"] = "customer_opt_out"
        _log_stop_reason(chat_id, "customer_opt_out", dry_run)
        return "opt_out", ok

    if category == "phone":
        # شرط الإيقاف 2: رقم واتساب → رسالة تأكيد مخصصة + إيقاف نهائي
        _save_phone_and_notify(chat_id, phone, now_iso, dry_run)
        ok, err = _send_message(agent, conv, MSG_PHONE_CONFIRM, dry_run)
        entry["stopped"] = True
        entry["stop_reason"] = f"phone_received:{phone}"
        return "phone", ok

    if category == "booking":
        # شرط الإيقاف 3: أكمل الحجز / دفع جدية الحجز → تحويل لمسار الحجز
        _transfer_to_booking(chat_id, "booking_confirmed_or_deposit", now_iso, dry_run)
        entry["stopped"] = True
        entry["stop_reason"] = "booking_confirmed"
        return "booking", False

    # شرط الإيقاف 1: أي رد آخر → أجب على استفساره بشكل طبيعي (المساعد الأساسي
    # يرد مباشرة)، ثم يبدأ حساب الساعات من جديد من آخر رسالة للعميل، مع
    # احتساب المتابعات السابقة ضمن الحد الأقصى الكلي 3.
    _reset_anchor(entry, new_ts, text, now_iso)
    return "reply", False


# =============================================================================
# منطق جدول القرارات (جدول المدير حرفياً)
# =============================================================================
def _due_stage(entry: dict, now: datetime, last_customer_ts: datetime) -> int:
    """تحديد المرحلة المستحقة (واحدة فقط لكل محادثة في كل تشغيل) حسب جدول
    قرارات المدير:
    - أقل من 1 ساعة → 0 (انتظر الدورة القادمة).
    - من 1 إلى أقل من 6 ساعات + 0 متابعات → المرحلة 1.
    - من 6 إلى أقل من 21 ساعة + 0 أو 1 متابعات → المرحلة 2
      (إن لم تُرسل 1 نرسل 2 مباشرة ولا نعوّض 1).
    - من 21 إلى أقل من 24 ساعة + 0/1/2 متابعات → المرحلة 3 (الإغلاق).
    - 24 ساعة أو أكثر → -1 (نافذة ميتا مقفولة — توقف نهائي).
    - 3 متابعات → 0 (بلغ الحد الأقصى الكلي — لا مزيد أبداً).
    يعيد رقم المرحلة (1/2/3) أو 0 أو -1.
    """
    count = int(entry.get("sent_count") or 0)
    if count >= MAX_FOLLOWUPS_TOTAL:
        return 0  # الحد الأقصى 3 رسائل متابعة لكل محادثة — لا مزيد

    elapsed = (now - last_customer_ts).total_seconds() / 3600.0

    if elapsed < 1.0:
        return 0  # أقل من 1 ساعة → انتظر
    if elapsed >= WINDOW_HARD_STOP_HOURS:
        return -1  # 24 ساعة أو أكثر → توقف نهائي (لا إرسال)

    if count == 0 and STAGE1_MIN_HOURS <= elapsed < STAGE1_MAX_HOURS:
        return 1
    if count <= 1 and STAGE2_MIN_HOURS <= elapsed < STAGE2_MAX_HOURS:
        return 2
    if count <= 2 and STAGE3_MIN_HOURS <= elapsed < STAGE3_MAX_HOURS:
        return 3
    return 0


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
    actions = {"stage1": 0, "stage2": 0, "stage3": 0, "opt_out": 0,
               "phone": 0, "booking": 0, "reply_reset": 0, "window_closed": 0}

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        msg = f"Failed to connect to DB: {e}"
        log.error(f"[HajjEarlyBooking] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}

    state = _load_state()
    chats = state.setdefault("chats", {})
    opted_out_senders = state.setdefault("opted_out_senders", {})

    try:
        conversations = _get_ad_conversations(cursor, now)
        log.info(f"[HajjEarlyBooking] Found {len(conversations)} recent conversations for ad {TARGET_AD_ID}")

        for conv in conversations:
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue
            if limit and processed_chats >= limit:
                break

            # ===== 5) تدخّل موظف بشري → إيقاف السلسلة نهائياً =====
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

            # ===== مرساة الوقت: آخر رسالة حقيقية من العميل =====
            last_cust_text, last_cust_raw = _last_real_customer_message(cursor, chat_id)
            if last_cust_raw is None:
                continue
            last_cust_ts = _parse_dt(last_cust_raw)
            if last_cust_ts is None:
                continue

            sender_id = str(conv.get("sender_identifier") or "").strip()
            processed_chats += 1

            # ===== 6) عميل محفوظ له customer_phone → إيقاف نهائي =====
            # حتى لو فُقد ملف الحالة، لا نرسل أي متابعة لعميل سبق أن أرسل رقمه
            # وتحوّل لمسار «Lead جاهز للاتصال» (قاعدة المدير: رقم → إيقاف نهائي).
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
                    entry = _init_entry(conv, last_cust_ts, last_cust_text, now_iso)
                    entry["sender_identifier"] = sender_id
                    entry["stopped"] = True
                    entry["stop_reason"] = f"phone_already_on_record:{existing_phone}"
                    entry["updated_at"] = now_iso
                    chats[chat_id] = entry
                    if not dry_run:
                        _save_state(state)
                continue

            # ===== إيقاف محادثة قيد السلسلة لمرسل طلب الإيقاف الدائم =====
            entry = chats.get(chat_id)
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
                # مرسل سبق وطلب عدم التواصل → لا نرسل له متابعات نهائياً
                if sender_id and sender_id in opted_out_senders:
                    continue
                entry = _init_entry(conv, last_cust_ts, last_cust_text, now_iso)
                entry["sender_identifier"] = sender_id
                chats[chat_id] = entry
                if not dry_run:
                    _save_state(state)
                # أول رسالة قد تحتوي طلب إيقاف / رقم / نية حجز — نعالجها فوراً
                if not _is_media_placeholder(last_cust_text):
                    cat, sent = _handle_new_message(agent, conv, entry, last_cust_text, last_cust_ts, now_iso, dry_run)
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
                    # لو أُرسلت رسالة بالفعل في هذه الدورة → لا نرسل مرحلة في
                    # نفس التشغيل (قاعدة: رسالة واحدة كحد أقصى في الدورة الواحدة)
                    if sent:
                        continue
                    # بعد المعالجة نكمل لنفس منطق الجدولة (قد تكون متابعة
                    # مستحقة فعلاً إن مرّ وقت كافٍ على آخر رسالة العميل)

            # ===== كشف رد جديد من العميل أثناء السلسلة → معالجة حسب الشروط =====
            prev_anchor = _parse_dt(entry.get("last_customer_reply"))
            if (not is_new_entry) and (prev_anchor is None or last_cust_ts > prev_anchor):
                # حماية من التكرار: لو كانت السلسلة موقوفة إيقافاً دائماً (رقم /
                # حجز / opt-out / تدخّل بشري) فلا نرسل أي رسالة حتى لو أرسل العميل
                # رسالة جديدة (قاعدة المدير: لا تكرر رسالة سبق إرسالها أبداً —
                # مثال: عميل أرسل رقمه ووصلته رسالة التأكيد ثم أرسل رقماً آخر،
                # لا نرسل التأكيد مرة ثانية). أما الإيقاف المؤقت (window_closed)
                # فرسالة العميل الجديدة تفتح نافذة Meta جديدة → نتابع المعالجة
                # (تتعامل معها _handle_new_message عبر _reset_anchor).
                if entry.get("stopped") and entry.get("stop_reason") != "window_closed":
                    continue
                cat, sent = _handle_new_message(agent, conv, entry, last_cust_text, last_cust_ts, now_iso, dry_run)
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
                # لو أُرسلت رسالة بالفعل في هذه الدورة → لا نرسل مرحلة
                if sent:
                    continue

            # ===== حالة نهائية: أُوقفت السلسلة → لا نعيد =====
            if entry.get("stopped"):
                continue

            # ===== حماية ذاتية (Self-Healing): مزامنة الحالة من قاعدة
            # البيانات الفعلية للمحادثات الجديدة فقط (ملف الحالة مفقود/أُعيد
            # ضبطه) — حتى لا تتكرر أي رسالة سبق إرسالها من نسخة سابقة =====
            if is_new_entry:
                try:
                    if _sync_sent_state(cursor, chat_id, entry):
                        if not dry_run:
                            _save_state(state)
                except Exception as e:
                    log.warning(f"Failed to sync sent state for {chat_id}: {e}")
                if entry.get("stopped"):
                    continue

            # ===== لا رد جديد → منطق جدول القرارات الزمنية =====
            # المرساة = آخر رسالة حقيقية من العميل (وليس آخر رسالة منّا)
            last_anchor_ts = _parse_dt(entry.get("last_customer_reply")) or last_cust_ts
            elapsed_cust = (now - last_anchor_ts).total_seconds() / 3600.0

            # نافذة الـ 24 ساعة انتهت (أو أكثر) → توقف نهائي حتى يرد العميل
            # برسالة جديدة تفتح نافذة جديدة (نُبقي السجل في الحالة مع السبب)
            if elapsed_cust >= WINDOW_HARD_STOP_HOURS:
                entry["stopped"] = True
                entry["stop_reason"] = "window_closed"
                entry["updated_at"] = now_iso
                actions["window_closed"] = actions.get("window_closed", 0) + 1
                if not dry_run:
                    _save_state(state)
                continue

            target = _due_stage(entry, now, last_anchor_ts)
            if target == -1:
                # احتياط إضافي (يُلتقط قبل ذلك أصلاً) — لا إرسال بعد 24 ساعة
                entry["stopped"] = True
                entry["stop_reason"] = "window_closed"
                entry["updated_at"] = now_iso
                actions["window_closed"] = actions.get("window_closed", 0) + 1
                if not dry_run:
                    _save_state(state)
                continue
            if target == 0:
                continue

            msg = STAGE_MESSAGES.get(target, "")
            if not msg:
                continue

            ok, err = _send_message(agent, conv, msg, dry_run)
            if ok:
                entry["sent_count"] = int(entry.get("sent_count") or 0) + 1
                entry["updated_at"] = now_iso
                key = f"stage{target}"
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
        log.info(f"[HajjEarlyBooking] {message}")
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "processed_chats": processed_chats,
            "actions": actions,
            "errors": errors[:20],
            "message": message,
        }
    except Exception as e:
        msg = f"Error in Hajj early-booking follow-up run: {e}"
        log.error(f"[HajjEarlyBooking] {msg}")
        return {"ok": False, "sent_count": sent_count, "errors": [msg], "message": msg}
    finally:
        try:
            if not dry_run:
                _save_state(state)
            conn.close()
        except Exception:
            pass
