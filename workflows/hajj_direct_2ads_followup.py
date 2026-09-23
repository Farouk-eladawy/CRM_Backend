# -*- coding: utf-8 -*-
"""
Workflow: Religious Hajj Direct 2-Ads Follow-Up - ديني (إعلان الحج المباشر)
==========================================================================
تسلسل رسائل فولو أب لعملاء إعلان "الحج المباشر" (إعلانان فقط).

الإعلانات المستهدفة (شرط التفعيل الحصري — فلترة صارمة من الجذور في SQL):
    Ad ID: 120248934377370757
    Ad ID: 120248934520430757

شرط بدء التسلسل:
    بعد أن يُرسل للعميل شرح برنامج الحج المباشر (توجد رسالة agent/ai بعد آخر
    رسالة حقيقية للعميل)، والعميل لم يردّ ولم يرسل رقم تليفونه.

مواعيد الإرسال (محسوبة من وقت آخر رسالة أرسلها العميل — وليس من وقت ردنا):
    الرسالة ١: بعد ٣ ساعات
    الرسالة ٢: بعد ١٠ ساعات
    الرسالة ٣: بعد ٢١ ساعة
    ممنوع أي إرسال بعد مرور ٢٣ ساعة على آخر رسالة من العميل (نافذة Meta 24h).

قواعد صارمة:
    - الرسائل تُرسل بالترتيب، وممنوع إرسال رسالتين وراء بعض (رسالة واحدة لكل
      محادثة في الدورة الواحدة + تتبّع highest_stage_sent).
    - لا تُكرر رسالة سبق إرسالها أبداً.
    - لا تتداخل مع موظف بشري: نتخطى needs_help=1 / is_closed=1 / sales_inbox=1
      / auto_reply_hold_until في المستقبل.

إيقاف التسلسل فوراً (نهائياً) عند:
    1) العميل ردّ بأي رسالة في أي وقت → نتوقف ونتعامل مع الرد حسب القسم ٧.
    2) العميل أرسل رقم تليفونه → رسالة تأكيد + تحويل لموظف المبيعات + توقف.
    3) العميل قال إنه مش مهتم أو طلب عدم الإرسال → رسالة ختام + توقف.
    4) المحادثة تحوّلت لموظف مبيعات (needs_help/sales_inbox) → توقف.
    5) عدّى يوم الأربعاء ٣٠ سبتمبر (انتهى التقديم) → ماتبعتش أي رسالة بعدها.
    6) العميل قال "السنة دي مش مناسبة" → شكر + تعليمه كعميل مهتم بحج السنة
       الجاية + توقف نهائي.

قاعدة التاريخ:
    آخر موعد تقديم هو الأربعاء ٣٠ سبتمبر. في أي مكان في الرسائل مكتوب فيه
    "يوم الأربعاء ٣٠ سبتمبر":
      - لو الإرسال يوم الثلاثاء ٢٩ سبتمبر → "بكرة الأربعاء ٣٠ سبتمبر".
      - لو الإرسال يوم الأربعاء ٣٠ سبتمبر → "النهارده الأربعاء ٣٠ سبتمبر".
      - غير ذلك → تبقى كما هي "يوم الأربعاء ٣٠ سبتمبر".

ملاحظات هندسية (قواعد النظام):
    - التوقيت: chat_db.get_cairo_time() (توقيت القاهرة UTC+3) — قاعدة النظام F
      (ممنوع datetime.now(timezone.utc)).
    - الحالة: ملف JSON محلي عبر fts_paths.get_data_path — قاعدة النظام G
      (يُمنع agent.load_state/save_state في run_script).
    - نصوص الرسائل تُرسل كما هي بالحرف بدون أي Markdown وكل الأرقام عربية.
    - ممنوع طلب صورة البطاقة على ماسنجر، وممنوع أكثر من سؤال في الرسالة الواحدة.
"""

import os
import re
import sys
import json
import time
import sqlite3
import logging
import threading
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ثوابت السير العمل
# =============================================================================
# الإعلانان المستهدفان حصرياً (شرط التفعيل من الجذور)
TARGET_AD_IDS = [
    "120248934377370757",
    "120248934520430757",
]

# قاعدة بيانات المحادثات (نفس مسار chat_db)
DB_FILE = get_data_path("chat_history.db")

# ملف الحالة المحلي (قاعدة النظام G: يُمنع agent.load_state)
STATE_FILE = get_data_path("hajj_direct_2ads_followup_state.json")

# عتبات التوقيت بالساعات (مقاسة من آخر رسالة من العميل)
STAGE1_HOURS = 3.0       # الرسالة ١: بعد ٣ ساعات
STAGE2_HOURS = 10.0      # الرسالة ٢: بعد ١٠ ساعات
STAGE3_HOURS = 21.0      # الرسالة ٣: بعد ٢١ ساعة
NO_SEND_AFTER_HOURS = 23.0   # ممنوع الإرسال بعد مرور ٢٣ ساعة
WINDOW_HOURS = 24.0          # نافذة Meta الكاملة (أمان من خطأ #10)

# آخر موعد تقديم: الأربعاء ٣٠ سبتمبر (بعد انتهاء هذا اليوم نتوقف نهائياً)
DEADLINE_YEAR = 2026
DEADLINE_MONTH = 9
DEADLINE_DAY = 30

# حد أقصى للإرسال في كل تشغيل (حتى لا يتجاوز timeout الـ http_request)
MAX_SENDS_PER_RUN = 20

# الـ tags المستخدمة
TAG_NO_RESPONSE = "no-response-hajj-direct-2ads"
TAG_HOT_LEAD = "hajj-direct-2ads-hot-lead"
TAG_NEXT_YEAR = "hajj-direct-interested-next-year"

log = logging.getLogger("HajjDirect2AdsFollowup")

# =============================================================================
# نصوص الرسائل الثلاث (كما هي بالحرف — لا تغيير ولا إعادة صياغة ولا Markdown)
# ملاحظة: الأرقام كلها بالأرقام العربية كما وردت.
# =============================================================================
MSG_FOLLOWUP_1 = (
    "السلام عليكم ورحمة الله\n"
    "حبيت أتأكد إن تفاصيل برنامج الحج المباشر وصلت لحضرتك.\n"
    "\n"
    "للعلم: فاضل معانا آخر ١٠ أماكن، والتقديم بيقفل يوم الأربعاء ٣٠ سبتمبر.\n"
    "\n"
    "حضرتك مهتم بأنهي برنامج؟\n"
    "١- الطيران الاقتصادي: ٥٢٠ ألف جنيه\n"
    "٢- الطيران التحسين (٧ أيام): ٥٥٠ ألف جنيه\n"
    "\n"
    "ابعتلي رقم البرنامج، وأنا أحجز لحضرتك مكان وأكلمك أكمّل معاك."
)

MSG_FOLLOWUP_2 = (
    "معلومة مهمة لحضرتك قبل ما تقرر:\n"
    "\n"
    "تأشيرات الحج المباشر عددها قليل جدًا.\n"
    "الأسبوع الجاي الوزارة هتطلب دفع قيمة التأشيرة (٥٠٠٠ دولار)، وبتدي مهلة ٤ أيام بس، ولو ما اتدفعتش في المهلة التأشيرة بتتسحب وتروح لحد تاني.\n"
    "\n"
    "عشان كده لازم نخلّص أوراق حضرتك قبل ما الوزارة تطلب الدفع، وآخر موعد للحجز يوم الأربعاء ٣٠ سبتمبر.\n"
    "\n"
    "ابعتلي رقم تليفون حضرتك، وأنا أكلمك وأشرح لك الخطوات بالظبط."
)

MSG_FOLLOWUP_3 = (
    "فاضل معانا ١٠ أماكن بس في الحج المباشر، والتقديم بيقفل يوم الأربعاء ٣٠ سبتمبر.\n"
    "\n"
    "لو حضرتك ناوي تحج السنة دي، ابعتلي رقمك دلوقتي وهكلمك خلال ساعة.\n"
    "\n"
    "ولو السنة دي مش مناسبة، قولّي وأنا أبلّغ حضرتك أول ما برنامج السنة الجاية يفتح."
)

# رسائل التعامل مع ردود العميل على التسلسل (القسم ٧)
MSG_PHONE_CONFIRM = (
    "تمام يا فندم، وصلني رقم حضرتك 🧡 حد من فريق المبيعات هيتواصل معاك في أقرب وقت. شكرًا لثقة حضرتك في FTS للسياحة 🕋"
)

MSG_DISINTEREST = (
    "تحت أمر حضرتك في أي وقت 🧡 ولو حبيت تسأل عن برامج الحج أو العمرة مستقبلًا، إحنا موجودين دايمًا في خدمتك. ربنا يكرمك ويرزقك زيارة بيته الحرام 🕋"
)

MSG_NEXT_YEAR = (
    "تحت أمر حضرتك 🧡 سجّلت حضرتك كعميل مهتم بحج السنة الجاية، وأول ما البرنامج يفتح هنبلّغ حضرتك فورًا. ربنا يكتبلك الحج في أقرب وقت 🕋"
)

# سؤال واحد فقط (ممنوع أكثر من سؤال في الرسالة الواحدة) عند اختيار العميل لبرنامج
MSG_ASK_PHONE = (
    "تمام يا فندم، سجّلت اختيار حضرتك لبرنامج {program} 🕋 ابعتلي رقم تليفونك وأنا أكلمك أكمّل معاك."
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


def _deadline_passed(now) -> bool:
    """هل انتهى يوم الأربعاء ٣٠ سبتمبر (انتهى التقديم)؟ نتوقف نهائياً بعده."""
    try:
        return now.date() > datetime(DEADLINE_YEAR, DEADLINE_MONTH, DEADLINE_DAY).date()
    except Exception:
        return False


def _apply_date_rule(text: str, send_dt) -> str:
    """تطبيق قاعدة التاريخ على عبارة "يوم الأربعاء ٣٠ سبتمبر" حسب يوم الإرسال.
    - الثلاثاء ٢٩ سبتمبر → "بكرة الأربعاء ٣٠ سبتمبر".
    - الأربعاء ٣٠ سبتمبر → "النهارده الأربعاء ٣٠ سبتمبر".
    - غير ذلك → كما هي.
    ممنوع تغيير أي شيء آخر في نص الرسالة.
    """
    phrase = "يوم الأربعاء ٣٠ سبتمبر"
    try:
        d = send_dt.date()
    except Exception:
        return text
    if d == datetime(2026, 9, 29).date():
        return text.replace(phrase, "بكرة الأربعاء ٣٠ سبتمبر")
    if d == datetime(2026, 9, 30).date():
        return text.replace(phrase, "النهارده الأربعاء ٣٠ سبتمبر")
    return text


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
if not hasattr(sys, "_hajj_direct_2ads_followup_state_lock"):
    sys._hajj_direct_2ads_followup_state_lock = threading.Lock()
_STATE_LOCK = sys._hajj_direct_2ads_followup_state_lock


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
    if t.startswith("[Facebook Ad Referral]") or t.startswith("[Facebook Referral]"):
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
        "[proposed_draft]",
        "[escalate]",
        "[auto]",
    )
    return any(low.startswith(p) for p in prefixes)


# أنماط طلب إيقاف التواصل نهائياً
_OPTOUT_PATTERNS = (
    r"متبعتليش", r"متبعتلوش", r"متكلمنيش", r"متكلمناش", r"متزعجنيش",
    r"بلاش تبعت", r"بلاش رسا[يئ]ل", r"مش عايز رسا[يئ]ل", r"مش عايز اتصالات",
    r"مش مهتم", r"اوقفوا", r"اوقفو", r"وقفو", r"لا ترسل", r"لا تبعث",
    r"شيلني", r"انزعني", r"\bstop\b", r"\bunsubscribe\b", r"don'?t contact",
    r"no more messages", r"ممنوع ترسل", r"بطلوا رسا[يئ]ل", r"بطلت رسا[يئ]ل",
    r"شكر[اًا]?.*مش عايز", r"مش عايز منكم", r"مش عايز حاجة", r"مش عايز اي حاجة",
    r"مش عايز حج", r"مش عايز سفر", r"مش عايز عمرة", r"مش عايز حد يكلمني",
)


def _is_optout(text: str) -> bool:
    """كشف طلب العميل إيقاف التواصل نهائياً."""
    norm = _normalize_keyword(text)
    for p in _OPTOUT_PATTERNS:
        if re.search(p, norm):
            return True
    return False


# أنماط "السنة دي مش مناسبة" (عميل مهتم بحج السنة الجاية — إيقاف نهائي)
_NEXT_YEAR_PATTERNS = (
    r"السنه (دي|دى) مش مناس",
    r"السنه الجايه", r"السنه الجاية", r"السنة الجايه", r"السنة الجاية",
    r"مش هحج السنه", r"مش هحج السنة", r"مش هقدر السنه", r"مش هقدر السنة",
    r"مش مناسب السنه", r"مش مناسب السنة",
)


def _is_next_year(text: str) -> bool:
    """هل قال العميل إن السنة دي مش مناسبة (نعلّمه مهتم بحج السنة الجاية)؟"""
    norm = _normalize_keyword(text)
    for p in _NEXT_YEAR_PATTERNS:
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


def _detect_program_choice(text: str):
    """كشف اختيار العميل للبرنامج: "١"/"1" أو ذكر اسم البرنامج."""
    norm = _normalize_keyword(text)
    if re.fullmatch(r"1", norm) or "الاقتصادي" in norm or "اقتصادي" in norm:
        return "الطيران الاقتصادي"
    if re.fullmatch(r"2", norm) or "التحسين" in norm or "تحسين" in norm:
        return "الطيران التحسين"
    return None


# =============================================================================
# استعلامات قاعدة البيانات (فلترة صارمة من الجذور — قاعدة النظام 15)
# =============================================================================
def _get_ad_conversations(cursor):
    """المحادثات الواردة من الإعلانين فقط (شرط التفعيل الحصري).
    الفلترة تتم في SQL من الجذور (facebook_ad_id IN (...)) وليس برمجياً.
    """
    placeholders = ",".join("?" * len(TARGET_AD_IDS))
    cursor.execute(
        f"""
        SELECT chat_id, sender_identifier, contact_name, source, location,
               receiving_phone_id, last_message_time, needs_help, is_closed,
               auto_reply_hold_until, customer_phone, sales_inbox
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
    """كل رسائل العميل الحقيقية في المحادثة (نص، توقيت) تصاعدياً."""
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


def _last_agent_ts(cursor, chat_id):
    """توقيت آخر رسالة حقيقية من الفريق/الـ agent (شرح البرنامج)."""
    cursor.execute(
        """
        SELECT text, timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type IN ('agent', 'ai')
        ORDER BY timestamp DESC
        LIMIT 20
        """,
        (chat_id,),
    )
    for row in cursor.fetchall():
        text, ts = str(row[0] or ""), row[1]
        if _is_referral_or_media(text):
            continue
        return _parse_dt(ts)
    return None


def _has_agent_between(cursor, chat_id, ts1, ts2) -> bool:
    """هل توجد رسالة agent/ai بين توقيتين؟ (لكشف أن آخر رسالة عميل هي رد علينا)."""
    d1, d2 = _parse_dt(ts1), _parse_dt(ts2)
    if d1 is None or d2 is None:
        return False
    cursor.execute(
        """
        SELECT timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type IN ('agent', 'ai')
        """,
        (chat_id,),
    )
    for row in cursor.fetchall():
        d = _parse_dt(row[0])
        if d is not None and d1 < d < d2:
            return True
    return False


def _hold_active(hold_until, now) -> bool:
    """هل فترة إيقاف الرد الآلي (auto_reply_hold_until) ما زالت سارية؟"""
    if not hold_until:
        return False
    d = _parse_dt(hold_until)
    return bool(d and d > now)


# =============================================================================
# منطق جدول المواعيد
# =============================================================================
def _target_stage(elapsed_h: float, highest_sent: int):
    """المرحلة المستحقة بناءً على الساعات المنقضية من آخر رسالة للعميل.
    القاعدة: رسالة واحدة كحد أقصى في الدورة، ولا تكرار، والحد ٣ رسائل.
    """
    if elapsed_h < STAGE1_HOURS:
        return None                                        # لم يمضِ ٣ ساعات
    if elapsed_h < STAGE2_HOURS:
        return 1 if highest_sent < 1 else None             # [٣, ١٠) → الرسالة ١
    if elapsed_h < STAGE3_HOURS:
        return 2 if highest_sent < 2 else None             # [١٠, ٢١) → الرسالة ٢
    if elapsed_h < NO_SEND_AFTER_HOURS:
        return 3 if highest_sent < 3 else None             # [٢١, ٢٣) → الرسالة ٣
    return None  # >= ٢٣ ساعة: ممنوع الإرسال (نافذة Meta على وشك الإغلاق)


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
def _send_message(agent, conv: dict, text: str, now_dt, dry_run: bool = False):
    """إرسال الرسالة عبر القناة الصحيحة (Facebook / WhatsApp) وتسجيلها في السجل.
    يُطبَّق قاعدة التاريخ على النص قبل الإرسال.
    """
    if dry_run:
        return True, None
    text = _apply_date_rule(text, now_dt)
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


def _transfer_to_customer_service(chat_id: str, reason: str, phone: str = None,
                                  dry_run: bool = False, tag: str = TAG_HOT_LEAD):
    """تحويل المحادثة لموظف المبيعات: needs_help=1 + تسجيل الـ lead في sales_customer_state."""
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
        if tag and tag not in tags:
            tags = (tags + "," + tag) if tags else tag
        chat_db.upsert_sales_state(chat_id, {"tags": tags, "lead_status": "new"})
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Follow-up workflow: transferred to sales ({reason})",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to transfer {chat_id}: {e}")


def _tag_next_year(chat_id: str, dry_run: bool = False):
    """تعليم العميل كعميل مهتم بحج السنة الجاية + إيقاف نهائي."""
    if dry_run:
        return
    try:
        import chat_db
        existing = chat_db.get_sales_state(chat_id) or {}
        tags = str(existing.get("tags") or "")
        if TAG_NEXT_YEAR not in tags:
            tags = (tags + "," + TAG_NEXT_YEAR) if tags else TAG_NEXT_YEAR
        chat_db.upsert_sales_state(chat_id, {"tags": tags, "lead_status": "interested_next_year"})
        chat_db.add_message(
            chat_id,
            "agent",
            f"[System Log] Tagged: {TAG_NEXT_YEAR} (customer not suitable this year)",
            status="sent",
            source="System",
        )
    except Exception as e:
        log.error(f"Failed to tag next-year {chat_id}: {e}")


def _apply_no_response_tag(chat_id: str, dry_run: bool = False):
    """وضع tag: no-response بعد اكتمال المتابعات بدون رد."""
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


# =============================================================================
# التعامل مع رد العميل على التسلسل (القسم ٧)
# =============================================================================
def _handle_customer_reply(agent, conv: dict, reply_text: str, entry: dict,
                           now_iso: str, dry_run: bool):
    """يُستدعى مرة واحدة عند كشف رد جديد من العميل.
    يوقف التسلسل نهائياً ثم يطبّق السلوك المطابق للرد.
    """
    chat_id = str(conv.get("chat_id") or "").strip()
    entry["stopped"] = True
    entry["updated_at"] = now_iso

    # ١) رقم تليفون → تأكيد + تحويل لموظف المبيعات
    phone = _extract_phone(reply_text)
    if phone:
        _send_message(agent, conv, MSG_PHONE_CONFIRM, _now(), dry_run)
        entry["stopped_reason"] = f"phone:{phone}"
        entry["transferred"] = True
        _transfer_to_customer_service(chat_id, reason="hot_lead_phone", phone=phone, dry_run=dry_run)
        return

    # ٢) طلب عدم الإرسال / عدم الاهتمام → رسالة ختام مهذبة
    if _is_optout(reply_text):
        _send_message(agent, conv, MSG_DISINTEREST, _now(), dry_run)
        entry["stopped_reason"] = "optout"
        return

    # ٣) "السنة دي مش مناسبة" → شكر + تعليمه مهتم بحج السنة الجاية
    if _is_next_year(reply_text):
        _send_message(agent, conv, MSG_NEXT_YEAR, _now(), dry_run)
        entry["stopped_reason"] = "next_year"
        entry["next_year_interested"] = True
        _tag_next_year(chat_id, dry_run)
        return

    # ٤) اختيار برنامج ("١"/"٢"/اسم البرنامج) → تسجيل الاختيار + طلب الرقم + تحويل
    program = _detect_program_choice(reply_text)
    if program:
        _send_message(agent, conv, MSG_ASK_PHONE.format(program=program), _now(), dry_run)
        entry["stopped_reason"] = f"program_choice:{program}"
        entry["chosen_program"] = program
        _transfer_to_customer_service(chat_id, reason=f"program_choice:{program}", dry_run=dry_run)
        return

    # ٥) أي رد آخر → نتوقف فقط (يتولى الفلو الأساسي/المساعد الرد)
    entry["stopped_reason"] = "customer_replied"


# =============================================================================
# تهيئة سجل الحالة
# =============================================================================
def _init_entry(last_text: str, last_ts, now_iso: str) -> dict:
    return {
        "last_customer_reply": last_ts.isoformat() if last_ts else now_iso,
        "highest_stage_sent": 0,
        "stages": {},
        "last_customer_text": str(last_text or "")[:200],
        "stopped": False,
        "stopped_reason": "",
        "transferred": False,
        "next_year_interested": False,
        "chosen_program": "",
        "sequence_done": False,
        "tagged": False,
        "updated_at": now_iso,
    }


# =============================================================================
# نقطة الدخول الرئيسية (يستدعيها محرك الأتمتة عبر run_script)
# =============================================================================
def run(agent, payload: dict = None) -> dict:
    """
    payload (اختياري):
        dry_run: إن كان True لا يُرسل ولا يحفظ الحالة (للاختبار فقط).
        limit:   عدد أقصى للمحادثات المعالجة في هذا التشغيل (للاختبار).
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
    actions = {"stop_optout": 0, "stop_phone": 0, "stop_next_year": 0,
               "reset_reply": 0, "tagged": 0, "program_choice": 0, "deadline_passed": 0}

    # انتهى التقديم (بعد الأربعاء ٣٠ سبتمبر) → لا نرسل أي رسالة من التسلسل
    deadline_passed = _deadline_passed(now)

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        msg = f"Failed to connect to DB: {e}"
        log.error(f"[HajjDirect2Ads] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}

    state = _load_state()
    chats = state.setdefault("chats", {})

    try:
        conversations = _get_ad_conversations(cursor)
        log.info(f"[HajjDirect2Ads] Found {len(conversations)} conversations for ads {TARGET_AD_IDS}")

        for conv in conversations:
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue
            if limit and processed_chats >= limit:
                break

            # ===== لا نتداخل مع موظف بشري / تحويل لمبيعات / محادثة مغلقة =====
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
            try:
                if int(conv.get("sales_inbox") or 0) == 1:
                    continue  # المحادثة اتحوّلت لموظف مبيعات → توقف
            except Exception:
                pass
            if _hold_active(conv.get("auto_reply_hold_until"), now):
                continue

            entry = chats.get(chat_id)

            # ===== تخطٍ سريع: محادثة غير متتبعة ونشاطها أقدم من نافذة الـ 24 ساعة =====
            if entry is None:
                lmt = _parse_dt(conv.get("last_message_time"))
                if lmt is None or (now - lmt).total_seconds() / 3600.0 > WINDOW_HOURS:
                    continue

            # ===== حالة نهائية: أُوقف أو اكتمل → لا نعيد =====
            if entry is not None and (entry.get("stopped") or entry.get("sequence_done")):
                processed_chats += 1
                continue

            # ===== لقطة رسائل العميل =====
            cust_msgs = _customer_messages(cursor, chat_id)
            if not cust_msgs:
                continue
            last_customer_text, last_ts_raw = cust_msgs[-1]
            last_customer_ts = _parse_dt(last_ts_raw)
            if last_customer_ts is None:
                continue

            last_agent_ts = _last_agent_ts(cursor, chat_id)

            # ===== محادثة جديدة: نحتاج التأكد أن شرح البرنامج أُرسل =====
            if entry is None:
                # كشف إن كانت آخر رسالة عميل هي رد على رسالة سابقة منا
                # (يوجد رد منا بين الرسالة السابقة والأخيرة) → رد حقيقي يقف التسلسل.
                replied_to_us = False
                if len(cust_msgs) >= 2:
                    replied_to_us = _has_agent_between(cursor, chat_id, cust_msgs[-2][1], last_ts_raw)
                # شرط بدء التسلسل: يوجد رد منا (شرح البرنامج) بعد آخر رسالة للعميل.
                # لو آخر رسالة هي رد على رسالتنا فنعالجها حتى لو رد agent عليها.
                if not replied_to_us and not (last_agent_ts and last_agent_ts > last_customer_ts):
                    # لم يُرسل الشرح بعد → ننتظر الدورة القادمة (لا إيقاف دائم)
                    continue
                entry = _init_entry(last_customer_text, last_customer_ts, now_iso)
                chats[chat_id] = entry
                processed_chats += 1
                if replied_to_us:
                    # العميل رد بالفعل → إيقاف فوري + التعامل مع الرد (القسم ٧)
                    _handle_customer_reply(agent, conv, last_customer_text, entry, now_iso, dry_run)
                    if entry.get("stopped_reason") == "optout":
                        actions["stop_optout"] += 1
                    elif entry.get("stopped_reason", "").startswith("phone"):
                        actions["stop_phone"] += 1
                    elif entry.get("stopped_reason") == "next_year":
                        actions["stop_next_year"] += 1
                    elif entry.get("stopped_reason", "").startswith("program_choice"):
                        actions["program_choice"] += 1
                    if not dry_run:
                        _save_state(state)
                    continue
                if not dry_run:
                    _save_state(state)
                # نستمر في نفس الدورة لحساب المرحلة المستحقة

            # ===== كشف رد جديد من العميل أثناء التسلسل (إيقاف فوري) =====
            prev_ts = _parse_dt(entry.get("last_customer_reply"))
            if prev_ts is None or last_customer_ts > prev_ts:
                _handle_customer_reply(agent, conv, last_customer_text, entry, now_iso, dry_run)
                reason = str(entry.get("stopped_reason") or "")
                if reason == "optout":
                    actions["stop_optout"] += 1
                elif reason.startswith("phone"):
                    actions["stop_phone"] += 1
                elif reason == "next_year":
                    actions["stop_next_year"] += 1
                elif reason.startswith("program_choice"):
                    actions["program_choice"] += 1
                else:
                    actions["reset_reply"] += 1
                entry["last_customer_reply"] = last_customer_ts.isoformat()
                entry["last_customer_text"] = str(last_customer_text or "")[:200]
                if not dry_run:
                    _save_state(state)
                if sent_count >= MAX_SENDS_PER_RUN:
                    break
                continue

            # ===== بعد انتهاء التقديم: توقف نهائي بدون أي إرسال =====
            if deadline_passed:
                entry["sequence_done"] = True
                entry["updated_at"] = now_iso
                actions["deadline_passed"] += 1
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                continue

            # ===== حساب الوقت المنقضي من آخر رسالة للعميل =====
            anchor = _parse_dt(entry.get("last_customer_reply")) or last_customer_ts
            elapsed_h = (now - anchor).total_seconds() / 3600.0
            highest = int(entry.get("highest_stage_sent") or 0)

            # نافذة الـ 24 ساعة انتهت: توقف نهائي
            if elapsed_h >= WINDOW_HOURS:
                if highest >= 1 and not entry.get("tagged"):
                    _apply_no_response_tag(chat_id, dry_run)
                    entry["tagged"] = True
                    entry["sequence_done"] = True
                    actions["tagged"] += 1
                elif highest == 0:
                    chats.pop(chat_id, None)
                entry["updated_at"] = now_iso
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                continue

            # نافذة الإغلاق [23, 24): لا إرسال
            if elapsed_h >= NO_SEND_AFTER_HOURS:
                processed_chats += 1
                continue

            target = _target_stage(elapsed_h, highest)
            if target is None or highest >= target:
                processed_chats += 1
                continue

            msg = _stage_message(target)
            ok, err = _send_message(agent, conv, msg, now, dry_run)
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
            f"| actions={actions} | errors={len(errors)} | deadline_passed={deadline_passed}"
        )
        log.info(f"[HajjDirect2Ads] {message}")
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "processed_chats": processed_chats,
            "actions": actions,
            "errors": errors[:20],
            "message": message,
        }
    except Exception as e:
        msg = f"Error in Hajj Direct 2-Ads follow-up run: {e}"
        log.error(f"[HajjDirect2Ads] {msg}")
        return {"ok": False, "sent_count": sent_count, "errors": [msg], "message": msg}
    finally:
        try:
            if not dry_run:
                _save_state(state)
            conn.close()
        except Exception:
            pass

