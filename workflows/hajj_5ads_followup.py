# -*- coding: utf-8 -*-
"""
Workflow: Religious Hajj 5-Ads Follow-Up - ديني (حج ١٤٤٨ - الإعلانات الخمسة)
============================================================================
نظام Follow-Up تلقائي (3 رسائل كحد أقصى) للإعلانات الثمانية التالية فقط:

    Ad ID: 120248310136470757
    Ad ID: 120248557092690757
    Ad ID: 120248587975700757
    Ad ID: 120247657321100757
    Ad ID: 120246971083700757   (إضافة المدير 2026-08-28)
    Ad ID: 120248310136460757   (إضافة المدير 2026-08-28)
    Ad ID: 120248650670790757   (إضافة المدير 2026-08-28)
    Ad ID: 120248655936910757   (إضافة المدير 2026-08-28)

شرط التفعيل (فلترة صارمة من الجذور في SQL - لا نلمس أي إعلان أو قسم آخر):
    WHERE facebook_ad_id IN (5 IDs) AND (is_deleted IS NULL OR is_deleted = 0)

آلية العمل (تُشغَّل مجدولة كل 60 دقيقة):
    1) نحسب عدد الساعات المنقضية منذ آخر رسالة أرسلها العميل (وليس من رسائلنا).
    2) نتحقق من عدد رسائل المتابعة المرسلة سابقاً (0 / 1 / 2 / 3).
    3) نطبّق جدول القرارات أدناه.

جدول القرارات (من مواصفات المدير حرفياً):
    الساعات منذ آخر رسالة من العميل | المتابعات المرسلة | الإجراء
    أقل من 1 ساعة                    | أي عدد            | لا ترسل شيئاً
    1 إلى أقل من 6                   | 0                 | أرسل المتابعة رقم 1
    6 إلى أقل من 21                  | 0 أو 1            | أرسل المتابعة رقم 2 (إن لم تُرسل 1، أرسل 2 مباشرة ولا تعوّض 1)
    21 إلى أقل من 24                 | 0 أو 1 أو 2       | أرسل المتابعة رقم 3 (رسالة الإغلاق)
    24 ساعة أو أكثر                  | أي عدد            | توقف نهائياً (انتهت نافذة Meta الـ 24 ساعة)

قواعد صارمة:
    - لا ترسل أكثر من رسالة متابعة واحدة في الدورة الواحدة.
    - لا تكرر رسالة سبق إرسالها أبداً.
    - الحد الأقصى 3 رسائل متابعة لكل محادثة (تُحتسب الرسائل السابقة ضمن الحد
      حتى لو رد العميل وأعدنا ضبط الساعات).

شروط إيقاف المتابعة فوراً:
    1) العميل رد بأي رسالة → يُعاد حساب الساعات من رسالته الأخيرة (المساعد
       الأساسي يجيب على استفساره)، وتُحتسب المتابعات السابقة ضمن الحد الأقصى.
    2) العميل أرسل رقم واتساب → رسالة التأكيد المخصصة + إيقاف نهائي + تحويل
       لموظف خدمة العملاء (يحتاج اتصالاً هاتفياً).
    3) العميل أكمل الحجز أو دفع جدية الحجز → إيقاف نهائي + تحويل لبشري.
    4) العميل عبّر عن عدم الاهتمام → رسالة الختام المهذب + إيقاف نهائي.

ملاحظات هندسية (لماذا هذه الشروط):
    - التوقيت: نستخدم chat_db.get_cairo_time() (توقيت القاهرة UTC+3) كما يفعل
      النظام بالكامل — قاعدة النظام F (ممنوع datetime.now(timezone.utc)).
    - الحالة: يُمنع agent.load_state/save_state (غير موجودة في run_script) لذا
      نستخدم ملف JSON محلي عبر fts_paths.get_data_path — قاعدة النظام G.
    - نافذة Meta: المرحلة 3 تُرسل بين الساعة 21 و 23.5 فقط (هامش أمان 30 دقيقة
      قبل إغلاق نافذة الـ 24 ساعة لتجنب خطأ Meta Error #10).
    - الحماية من التداخل البشري: نتخطى المحادثات التي بها needs_help=1 أو
      is_closed=1 أو auto_reply_hold_until في المستقبل.
    - حد أقصى للإرسال في كل تشغيل (MAX_SENDS_PER_RUN) حتى لا يتجاوز التشغيل
      timeout الـ http_request (60 ثانية) — التشغيل التالي يكمل الباقي لأن
      الحالة تُحفظ فور كل إرسال.
    - نصوص الرسائل تُرسل كما هي بالحرف (لا نعيد صياغتها) — من مواصفات المدير.
    - لا نكرر الأسعار في أي رسالة متابعة (العميل شاهدها في الرسالة الترحيبية).
"""

import os
import sys
import json
import re
import sqlite3
import logging
import time
import threading
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ثوابت السير العمل
# =============================================================================
# الإعلانات الثمانية المستهدفة فقط (شرط التفعيل الحصري)
# ملاحظة: المواصفات ذكرت 120248587975700757 مرتين (تكرار) — نُدرجه مرة واحدة.
# إضافة المدير (2026-08-28): 4 إعلانات جديدة تُطبَّق عليها نفس آلية الـ follow-up بالكامل.
TARGET_AD_IDS = [
    "120248310136470757",
    "120248557092690757",
    "120248587975700757",
    "120247657321100757",
    "120246971083700757",
    "120248310136460757",
    "120248650670790757",
    "120248655936910757",
]

# قاعدة بيانات المحادثات (نفس مسار chat_db)
DB_FILE = get_data_path("chat_history.db")

# ملف الحالة المحلي (قاعدة النظام G: يُمنع agent.load_state)
STATE_FILE = get_data_path("hajj_5ads_followup_state.json")

# عتبات التوقيت بالساعات (مقاسة من آخر رسالة من العميل — جدول القرارات)
HOURS_NO_SEND_BEFORE = 1.0      # أقل من ساعة: لا ترسل شيئاً
HOURS_STAGE1_MIN = 1.0          # المتابعة 1: من ساعة
HOURS_STAGE1_MAX = 6.0          # المتابعة 1: حتى أقل من 6 ساعات
HOURS_STAGE2_MIN = 6.0          # المتابعة 2: من 6 ساعات
HOURS_STAGE2_MAX = 21.0         # المتابعة 2: حتى أقل من 21 ساعة
HOURS_STAGE3_MIN = 21.0         # المتابعة 3: من 21 ساعة
HOURS_STAGE3_MAX = 23.5         # المتابعة 3: حتى 23.5 فقط (هامش أمان لنافذة Meta #10)
WINDOW_HOURS = 24.0             # نافذة Meta الكاملة: بعدها توقف نهائي مهما كانت الظروف

# حد أقصى للإرسال في كل تشغيل (حتى لا يتجاوز timeout الـ http_request)
MAX_SENDS_PER_RUN = 20

# الـ tag المطلوب وضعه عند اكتمال المتابعات الثلاث بدون رد
TAG_NO_RESPONSE = "no-response-hajj-5ads"
TAG_HOT_LEAD = "hajj-5ads-hot-lead"
TAG_PENDING_REPLY = "pending-reply-hajj-5ads"

log = logging.getLogger("Hajj5AdsFollowup")

# =============================================================================
# نصوص الرسائل (كما هي بالحرف — من مواصفات المدير، لا تغيير ولا إعادة صياغة)
# =============================================================================
MSG_FOLLOWUP_1 = (
    "اطمنا إن تفاصيل البرامج والأسعار وصلتك 🕋\n"
    "ومعظم اللي بيوصلهم التفاصيل بيبقى عندهم سؤال أو اتنين قبل ما ياخدوا القرار — عن السداد، أو الفنادق، أو مواعيد السفر، أو الفرق بين البرامج او تقدم في السياحه احسن ولا الداخليه ولا الجمعيات.\n"
    "\n"
    "اكتبلنا سؤالك هنا — أي سؤال — وهنجاوبك فورًا .\n"
    "ولو حابب اكلم حضرتك واشرحلك صوتي، ابعتلنا رقم الواتساب."
)

MSG_FOLLOWUP_2 = (
    "⚠️ معلومة مهمة لازم تعرفها قبل ٢٧ أغسطس:\n"
    "\n"
    "التقديم في حج ١٤٤٨ قناة واحدة بس — يعني اللي يقدّم في قرعة الداخلية (بتقفل الخميس ٢٧/٨) أو حج الجمعيات (بيقفل ٣١/٨) مش هيقدر يقدّم في الحج السياحي خالص السنة دي.\n"
    "\n"
    "وفرص القبول في الحج السياحي أعلى بكتير من القرعة — لأن الأعداد المتقدمة أقل بكتير.\n"
    "\n"
    "ومسجّلين الاهتمام معانا دلوقتي مبلغ الخصم متثبت باسمهم مهما كانت أسعار الضوابط الجديدة — يعني التسجيل المبكر مش مجرد أولوية، ده تثبيت فعلي.\n"
    "\n"
    "فقبل ما تحجز مكانك في أي قناة، اسألنا الأول — رد بأي سؤال وفريقنا هيوضحلك الفرق بالأرقام.\n"
    "\n"
    "FTS للسياحة — ترخيص وزارة السياحة فئة (أ) رقم ٢٠٨٩"
)

MSG_FOLLOWUP_3 = (
    "دي آخر رسالة نقدر نبعتهالك النهارده 🙏\n"
    "\n"
    "وقبل ما نسيبك، حاجتين كنا حابين يوصلوك:\n"
    "\n"
    "🎁 أي حد بيقدّم معانا في قرعة الحج السياحي بيدخل تلقائيًا سحب على ٣ عمرات مجانية + سحب تاني على تذكرة طيران أو العبّارة مجانًا\n"
    "\n"
    "🔒 واللي بيسجل قبل نزول ضوابط ١٤٤٨ مبلغ الخصم وأولوية مكانه بيتثبتوا باسمه .\n"
    "\n"
    "📱 ابعتلنا رقم تليفونك دلوقتي — وهتواصل معاك ، هجاوبك على أي سؤال، وبثبتلك ميزتك في دقيقة — من غير أي التزام.\n"
    "\n"
    "ولو عندك سؤال معين واقفك عن القرار، اكتبه مع الرقم وهجاوبك عليه في أسرع وقت."
)

# رسالة التأكيد المخصصة عندما يرسل العميل رقم واتساب
MSG_PHONE_CONFIRM = (
    "تمام يا فندم، وصلني رقم حضرتك 🧡 هيتواصل معاك على الواتساب في أقرب وقت بكل تفاصيل البرامج والخصم. شكرًا لثقة حضرتك في FTS للسياحة، وربنا يكتبلك الحج 🕋"
)

# رسالة الختام المهذب عندما يعبّر العميل عن عدم الاهتمام
MSG_DISINTEREST = (
    "تحت أمر حضرتك في أي وقت 🧡 ولو حبيت تسأل عن برامج الحج أو العمرة مستقبلًا، إحنا موجودين دايمًا في خدمتك. ربنا يكرمك ويرزقك زيارة بيته الحرام 🕋"
)

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
            if isinstance(data, dict) and "chats" in data:
                return data
            return {"chats": data if isinstance(data, dict) else {}}
    except Exception as e:
        log.error(f"Failed to load state: {e}")
    return {"chats": {}}


# قفل ثابت عبر إعادة تحميل الموديول (run_script يعيد exec_module في كل تشغيل)
if not hasattr(sys, "_hajj_5ads_followup_state_lock"):
    sys._hajj_5ads_followup_state_lock = threading.Lock()
_STATE_LOCK = sys._hajj_5ads_followup_state_lock


def _save_state(state: dict):
    """حفظ فوري بعد كل حدث مهم حتى لا نكرر الإرسال لو توقف التشغيل فجأة."""
    tmp_path = STATE_FILE + ".tmp"
    last_err = None
    with _STATE_LOCK:
        for attempt in range(6):
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, ensure_ascii=False)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
                os.replace(tmp_path, STATE_FILE)
                return
            except OSError as e:
                last_err = e
                # 22=EINVAL, 13=EACCES, 5=EIO — قفل مؤقت شائع على Windows
                if getattr(e, "errno", None) not in (5, 13, 22):
                    break
                time.sleep(0.05 * (attempt + 1))
            except Exception as e:
                last_err = e
                break
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        log.error(f"Failed to save state: {last_err}")


# =============================================================================
# أدوات النصوص والتطبيع
# =============================================================================
_AR_TRANS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ة": "ه", "ى": "ي"})
_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def _normalize_keyword(text: str) -> str:
    """تطبيع النص للمطابقة فقط (وليس للتغيير في الرسائل)."""
    s = str(text or "").strip().lower()
    s = re.sub(r"[\u064B-\u065F\u0640]", "", s)
    s = s.translate(_AR_TRANS).translate(_AR_DIGITS).translate(_FA_DIGITS)
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _is_referral_or_media(text: str) -> bool:
    """رسائل النظام/الميديا التي ليست تفاعلاً حقيقياً من العميل."""
    t = str(text or "").strip()
    if not t:
        return True
    if t.startswith("[Facebook Ad Referral]"):
        return True
    low = t.lower()
    prefixes = (
        "[customer sent an audio message",
        "[customer sent a video",
        "[customer sent a sticker",
        "[customer sent a document",
        "[customer sent a message of type",
        "[customer shared a location",
        "[customer shared contacts",
        "[system log",
        "[system]",
    )
    return any(low.startswith(p) for p in prefixes)


_OPTOUT_PATTERNS = (
    r"متبعتليش", r"متبعتلوش", r"متكلمنيش", r"متكلمناش", r"متزعجنيش",
    r"بلاش تبعت", r"بلاش رسا[يئ]ل", r"مش عايز رسا[يئ]ل", r"مش عايز اتصالات",
    r"مش مهتم", r"اوقفوا", r"اوقفو", r"وقفو", r"لا ترسل", r"لا تبعث",
    r"شيلني", r"انزعني", r"\bstop\b", r"\bunsubscribe\b", r"don'?t contact",
    r"no more messages", r"ممنوع ترسل", r"بطلوا رسا[يئ]ل", r"بطلت رسا[يئ]ل",
    # أمثلة المدير الحرفية: "شكرًا مش عايز" — نلتقطها مع تجنب إيقاف من يقول
    # "مش عايز تفاصيل أكتر" (طلب معلومات وليس رفضاً للتواصل):
    r"شكر[اًا]?.*مش عايز", r"مش عايز منكم", r"مش عايز حاجة", r"مش عايز اي حاجة",
    r"مش عايز حج", r"مش عايز سفر", r"مش عايز عمرة", r"مش عايز حد يكلمني",
)


def _is_optout(text: str) -> bool:
    """كشف طلب العميل إيقاف التواصل نهائياً (لا نرسل له مجدداً أبداً)."""
    norm = _normalize_keyword(text)
    for p in _OPTOUT_PATTERNS:
        if re.search(p, norm):
            return True
    return False


# أنماط إتمام الحجز أو دفع جدية الحجز (إيقاف نهائي)
# ملاحظة هندسية: نميّز بين "عايز أحجز" (نية مستقبلية — لا نوقف) و "حجزت/دفعت"
# (إتمام فعلي — نوقف). تم إضافة هذا الشرط لتجنب إيقاف المتابعة لمجرد رغبة العميل.
_BOOKING_DONE_PATTERNS = (
    r"حجزت", r"حجزنا", r"كملت الحجز", r"كمّلنا الحجز", r"تم الحجز",
    r"اتحجز", r"اتأكد الحجز", r"دفعت", r"دفعنا", r"سددت", r"سددنا",
    r"دفع.*جدية", r"جدية الحجز", r"خدت رقم الحجز", r"booked", r"\bpaid\b",
    r"payment done", r"completed the booking",
)


def _is_booking_done(text: str) -> bool:
    """هل أكمل العميل الحجز أو دفع جدية الحجز؟ (إيقاف المتابعة نهائياً)."""
    norm = _normalize_keyword(text)
    for p in _BOOKING_DONE_PATTERNS:
        if re.search(p, norm):
            return True
    return False


def _extract_phone(text: str):
    """استخراج رقم موبايل مصري (بأي صيغة: 010.. / 20 10.. / 002 10.. / +20 10..)."""
    s = _normalize_keyword(text)
    s = re.sub(r"[\s\-\.\(\)]", "", s)
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
    return digits if len(digits) >= 11 else None


# =============================================================================
# استعلامات قاعدة البيانات (فلترة صارمة من الجذور)
# =============================================================================
def _get_ad_conversations(cursor):
    """المحادثات الواردة من الإعلانات الخمسة فقط (شرط التفعيل الحصري).
    الفلترة تتم في SQL من الجذور (facebook_ad_id IN (...)) وليس برمجياً —
    لا نلمس أي إعلان أو قسم آخر (قاعدة النظام 9/15).
    """
    placeholders = ",".join("?" * len(TARGET_AD_IDS))
    cursor.execute(
        f"""
        SELECT chat_id, sender_identifier, contact_name, source, location,
               receiving_phone_id, last_message_time, needs_help, is_closed,
               auto_reply_hold_until, customer_phone
        FROM conversations
        WHERE facebook_ad_id IN ({placeholders})
          AND (is_deleted IS NULL OR is_deleted = 0)
          AND last_message_time IS NOT NULL
        ORDER BY last_message_time ASC
        """,
        TARGET_AD_IDS,
    )
    rows = cursor.fetchall()
    return [dict(r) for r in rows] if rows else []


def _customer_messages(cursor, chat_id, cap: int = 500):
    """كل رسائل العميل الحقيقية في المحادثة (نص، توقيت) تصاعدياً.
    نستبعد فقط رسائل الإحالة/النظام لأنها ليست تفاعلاً حقيقياً من العميل.
    """
    cursor.execute(
        """
        SELECT text, timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        ORDER BY timestamp ASC
        LIMIT ?
        """,
        (chat_id, cap),
    )
    out = []
    for row in cursor.fetchall():
        text, ts = str(row[0] or ""), row[1]
        if _is_referral_or_media(text):
            continue
        if not text.strip():
            continue
        out.append((text, ts))
    return out


def _hold_active(hold_until, now) -> bool:
    """هل فترة إيقاف الرد الآلي (auto_reply_hold_until) ما زالت سارية؟"""
    if not hold_until:
        return False
    d = _parse_dt(hold_until)
    return bool(d and d > now)


# =============================================================================
# منطق جدول القرارات
# =============================================================================
def _target_stage(elapsed_h: float, highest_sent: int):
    """جدول القرارات (من مواصفات المدير حرفياً) — يُعيد رقم المتابعة المستحقة
    (1/2/3) أو None. القاعدة: لا ترسل أكثر من رسالة واحدة في الدورة الواحدة،
    ولا تكرر رسالة سبق إرسالها، والحد الأقصى 3 رسائل.
    """
    if elapsed_h < HOURS_NO_SEND_BEFORE:
        return None                                    # أقل من ساعة: انتظر الدورة القادمة
    if elapsed_h < HOURS_STAGE1_MAX:
        return 1 if highest_sent < 1 else None         # من 1 إلى أقل من 6 ساعات و0 مرسل → المتابعة 1
    if elapsed_h < HOURS_STAGE2_MAX:
        return 2 if highest_sent < 2 else None         # من 6 إلى أقل من 21 و0 أو 1 → المتابعة 2
                                                       # (إن لم تُرسل 1، نرسل 2 مباشرة ولا نعوّض 1)
    if elapsed_h < HOURS_STAGE3_MAX:
        return 3 if highest_sent < 3 else None         # من 21 إلى أقل من 23.5 و0/1/2 → المتابعة 3 (الإغلاق)
    return None  # >= 23.5 ساعة: لا نرسل (نافذة الـ 24 ساعة على وشك الإغلاق — تجنب Error #10)


def _stage_message(stage: int) -> str:
    if stage == 1:
        return MSG_FOLLOWUP_1
    if stage == 2:
        return MSG_FOLLOWUP_2
    if stage == 3:
        return MSG_FOLLOWUP_3
    return ""


# =============================================================================
# الإرسال والتحويل والتاج
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


def _transfer_to_customer_service(chat_id: str, reason: str, phone: str = None, dry_run: bool = False, tag: str = None):
    """تحويل المحادثة لموظف خدمة العملاء:
    needs_help=1 (يوقف الرد الآلي ويُظهر المحادثة للموظف البشري)
    + تسجيل الـ lead في sales_customer_state.
    """
    if dry_run:
        return
    try:
        import chat_db
        if phone:
            try:
                chat_db.update_conversation_info(chat_id, customer_phone=phone)
            except Exception:
                pass
        chat_db.update_conversation_info(chat_id, needs_help=True)
        existing = chat_db.get_sales_state(chat_id) or {}
        tags = str(existing.get("tags") or "")
        use_tag = tag or TAG_HOT_LEAD
        if use_tag not in tags:
            tags = (tags + "," + use_tag) if tags else use_tag
        chat_db.upsert_sales_state(chat_id, {"tags": tags, "lead_status": "new"})
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Follow-up workflow: transferred to customer service ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to transfer {chat_id}: {e}")


def _apply_no_response_tag(chat_id: str, dry_run: bool = False):
    """وضع tag: no-response-hajj-5ads بعد اكتمال المتابعات الثلاث بدون رد."""
    if dry_run:
        return
    try:
        import chat_db
        existing = chat_db.get_sales_state(chat_id) or {}
        tags = str(existing.get("tags") or "")
        if TAG_NO_RESPONSE not in tags:
            tags = (tags + "," + TAG_NO_RESPONSE) if tags else TAG_NO_RESPONSE
            chat_db.upsert_sales_state(chat_id, {"tags": tags})
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Tagged: {TAG_NO_RESPONSE} (3-stage follow-up completed with no response)",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to tag {chat_id}: {e}")


def _init_entry(last_text: str, last_ts: datetime, now_iso: str) -> dict:
    """تهيئة سجل الحالة لمحادثة جديدة."""
    return {
        "last_customer_reply": last_ts.isoformat(),   # المرساة: آخر رسالة من العميل
        "highest_stage_sent": 0,                      # عدد المتابعات المرسلة (0-3)
        "stages": {},
        "last_customer_text": str(last_text or "")[:200],
        "opted_out": False,
        "handled": False,
        "handled_reason": "",
        "sequence_done": False,
        "tagged": False,
        "updated_at": now_iso,
    }


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
    actions = {"stop_optout": 0, "stop_phone": 0, "stop_booking": 0, "reset_reply": 0, "tagged": 0}

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        msg = f"Failed to connect to DB: {e}"
        log.error(f"[Hajj5Ads] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}

    state = _load_state()
    chats = state.setdefault("chats", {})

    try:
        conversations = _get_ad_conversations(cursor)
        log.info(f"[Hajj5Ads] Found {len(conversations)} conversations for ads {len(TARGET_AD_IDS)}")

        for conv in conversations:
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue
            if limit and processed_chats >= limit:
                break

            # ===== لا نتداخل مع موظف بشري أو محادثة مغلقة =====
            try:
                if int(conv.get("needs_help") or 0) == 1:
                    continue
            except Exception:
                pass
            try:
                if int(conv.get("is_closed") or 0) == 1:
                    continue
            except Exception:
                pass
            if _hold_active(conv.get("auto_reply_hold_until"), now):
                continue

            entry = chats.get(chat_id)

            # ===== تخطٍ سريع: محادثة غير متتبعة ونشاطها أقدم من نافذة الـ 24 ساعة =====
            # لا يمكن مراسلتها إطلاقاً (نافذة Meta مغلقة) → نتخطاها دون استعلامات إضافية.
            if entry is None:
                lmt = _parse_dt(conv.get("last_message_time"))
                if lmt is None or (now - lmt).total_seconds() / 3600.0 > WINDOW_HOURS:
                    continue

            # ===== حالة نهائية: أُوقفت أو اكتملت → لا نعيد =====
            if entry is not None and (entry.get("opted_out") or entry.get("handled") or entry.get("sequence_done")):
                processed_chats += 1
                continue

            # ===== لقطة رسائل العميل (استعلام واحد لكل محادثة) =====
            cust_msgs = _customer_messages(cursor, chat_id)
            if not cust_msgs:
                continue
            last_customer_text, last_ts_raw = cust_msgs[-1]
            last_customer_ts = _parse_dt(last_ts_raw)
            if last_customer_ts is None:
                continue

            # ===== فحص شروط الإيقاف "في أي وقت خلال المحادثة" =====
            # (العميل قد يكون أرسل الرقم/عدم الاهتمام/إتمام الحجز في رسالة أقدم)
            phone_anytime = None
            optout_anytime = None
            booking_anytime = None
            for t, _ts in cust_msgs:
                if phone_anytime is None:
                    phone_anytime = _extract_phone(t)
                if optout_anytime is None:
                    optout_anytime = t if _is_optout(t) else None
                if booking_anytime is None:
                    booking_anytime = t if _is_booking_done(t) else None
                if phone_anytime is not None and optout_anytime is not None and booking_anytime is not None:
                    break

            # ===== محادثة جديدة: تهيئة الحالة ثم فحص شروط الإيقاف فوراً =====
            if entry is None:
                entry = _init_entry(last_customer_text, last_customer_ts, now_iso)
                chats[chat_id] = entry
                processed_chats += 1
                if optout_anytime is not None:
                    # العميل عبّر عن عدم الاهتمام → رسالة الختام المهذب + إيقاف نهائي
                    entry["handled"] = True
                    entry["handled_reason"] = "optout_anytime"
                    _send_message(agent, conv, MSG_DISINTEREST, dry_run)
                    actions["stop_optout"] += 1
                    sent_count += 1
                elif phone_anytime is not None:
                    # العميل أرسل رقم واتساب → رسالة التأكيد + إيقاف نهائي + تحويل لبشري
                    entry["handled"] = True
                    entry["handled_reason"] = f"phone_anytime:{phone_anytime}"
                    _send_message(agent, conv, MSG_PHONE_CONFIRM, dry_run)
                    _transfer_to_customer_service(chat_id, reason="hot_lead_phone", phone=phone_anytime, dry_run=dry_run)
                    actions["stop_phone"] += 1
                    sent_count += 1
                elif booking_anytime is not None:
                    # العميل أكمل الحجز/دفع → إيقاف نهائي (الموظف البشري يكمل الإجراءات)
                    entry["handled"] = True
                    entry["handled_reason"] = "booking_done"
                    _transfer_to_customer_service(chat_id, reason="booking_done", dry_run=dry_run)
                    actions["stop_booking"] += 1
                entry["updated_at"] = now_iso
                if not dry_run:
                    _save_state(state)
                continue

            # ===== كشف رد جديد من العميل أثناء المتابعة =====
            prev_ts = _parse_dt(entry.get("last_customer_reply"))
            if prev_ts is None or last_customer_ts > prev_ts:
                # شروط الإيقاف تُفحص أولاً (أي وقت خلال المحادثة)
                if optout_anytime is not None:
                    entry["handled"] = True
                    entry["handled_reason"] = "optout"
                    _send_message(agent, conv, MSG_DISINTEREST, dry_run)
                    actions["stop_optout"] += 1
                    sent_count += 1
                elif phone_anytime is not None:
                    entry["handled"] = True
                    entry["handled_reason"] = f"phone:{phone_anytime}"
                    _send_message(agent, conv, MSG_PHONE_CONFIRM, dry_run)
                    _transfer_to_customer_service(chat_id, reason="hot_lead_phone", phone=phone_anytime, dry_run=dry_run)
                    actions["stop_phone"] += 1
                    sent_count += 1
                elif booking_anytime is not None:
                    entry["handled"] = True
                    entry["handled_reason"] = "booking_done"
                    _transfer_to_customer_service(chat_id, reason="booking_done", dry_run=dry_run)
                    actions["stop_booking"] += 1
                else:
                    # العميل رد بأي رسالة → يبدأ حساب الساعات من جديد من رسالته الأخيرة.
                    # (المساعد الأساسي يجيب على استفساره — لا نحشر متابعة في نفس الرد)
                    # تُحتسب المتابعات السابقة ضمن الحد الأقصى: لا نعيد ضبط highest_stage_sent
                    # (الإجمالي لا يتجاوز 3 رسائل متابعة مهما حدث).
                    entry["last_customer_reply"] = last_customer_ts.isoformat()
                    actions["reset_reply"] += 1
                entry["last_customer_text"] = str(last_customer_text or "")[:200]
                entry["updated_at"] = now_iso
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
                continue

            # ===== لا رد جديد → منطق جدول القرارات (المرساة = آخر رسالة عميل) =====
            anchor = _parse_dt(entry.get("last_customer_reply")) or last_customer_ts
            elapsed_h = (now - anchor).total_seconds() / 3600.0
            highest = int(entry.get("highest_stage_sent") or 0)

            # نافذة الـ 24 ساعة انتهت: توقف نهائي مهما كانت الظروف (قيود Meta)
            if elapsed_h >= WINDOW_HOURS:
                if highest >= 1 and not entry.get("tagged"):
                    # اكتملت المتابعات بدون رد → tag ونتوقف نهائياً
                    _apply_no_response_tag(chat_id, dry_run)
                    entry["tagged"] = True
                    entry["sequence_done"] = True
                    actions["tagged"] = actions.get("tagged", 0) + 1
                elif highest == 0:
                    # لم تُرسل أي متابعة أبداً → حذف السجل من الحالة (نافذة Meta مغلقة)
                    chats.pop(chat_id, None)
                entry["updated_at"] = now_iso
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                continue

            # نافذة الإغلاق [23.5, 24): لا إرسال، ننتظر لنرى هل سيرد العميل
            if elapsed_h >= HOURS_STAGE3_MAX:
                processed_chats += 1
                continue

            target = _target_stage(elapsed_h, highest)
            if target is None:
                processed_chats += 1
                continue
            if highest >= target:
                processed_chats += 1
                continue

            msg = _stage_message(target)
            ok, err = _send_message(agent, conv, msg, dry_run)
            if ok:
                entry["highest_stage_sent"] = target
                entry.setdefault("stages", {})[str(target)] = now_iso
                entry["updated_at"] = now_iso
                sent_count += 1
                processed_chats += 1
                if not dry_run:
                    _save_state(state)  # حفظ فوري بعد كل إرسال (منع التكرار)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
            else:
                errors.append(f"stage{target}->{chat_id}: {err}")
                processed_chats += 1

        message = (
            f"Ads({len(TARGET_AD_IDS)}): sent={sent_count} | processed={processed_chats} "
            f"| actions={actions} | errors={len(errors)}"
        )
        log.info(f"[Hajj5Ads] {message}")
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "processed_chats": processed_chats,
            "actions": actions,
            "errors": errors[:20],
            "message": message,
        }
    except Exception as e:
        msg = f"Error in Hajj 5-Ads follow-up run: {e}"
        log.error(f"[Hajj5Ads] {msg}")
        return {"ok": False, "sent_count": sent_count, "errors": [msg], "message": msg}
    finally:
        try:
            if not dry_run:
                _save_state(state)
            conn.close()
        except Exception:
            pass
