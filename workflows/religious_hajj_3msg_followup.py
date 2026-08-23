# -*- coding: utf-8 -*-
"""
Religious Hajj 3-Message Follow-up — 3 رسائل حج متابعة
======================================================
Workflow مخصص للقسم الديني (Religious ONLY - فلترة صارمة من الجذور).

الطلب (من المدير - 2026-08-23):
  - على أي رسالة تيجي من الإعلانات التالية فقط (4 إعلانات حج):
      120248310136460757
      120248557092680757
      120248587975700757
      120247657321100757
  - نرسل 3 رسائل متابعة بالترتيب (مقاسة من آخر رسالة حقيقية للعميل):
      فولو أب ١: بعد ساعة من آخر رسالة للعميل بدون رد
      فولو أب ٢: بعد ٨ ساعات
      فولو أب ٣: بعد ٢٢ ساعة (قبل قفل نافذة Meta الـ 24 ساعة بساعتين على الأقل — أمان)
  - لو العميل رد في أي وقت → السلسلة بتقف فوراً والنافذة بتتصفّر (لا مزيد من الإرسال).

قواعد النظام المطبقة:
  - التوقيت: chat_db.get_cairo_time() (توقيت القاهرة UTC+3) — ممنوع datetime.now(timezone.utc).
  - الحالة: ملف JSON محلي عبر fts_paths.get_data_path — ممنوع agent.load_state/save_state.
  - الفلترة من الجذور في SQL: facebook_ad_id IN (4 إعلانات) AND location = 'Religious'
    — لا يمس أي قسم آخر نهائياً.
  - نافذة Meta: أي رسالة متابعة منا لا تجدد نافذة الـ 24 ساعة (النافذة من آخر
    رسالة للعميل فقط) ⇒ توقيت المراحل الثلاثة كله من آخر رسالة للعميل.
  - الحماية من خطأ Meta #10: لا إرسال نهائياً بعد مرور 24 ساعة (تُعلَّم المحادثة
    كمنتهية لمنع التكرار اللانهائي).
  - لا نتداخل مع موظف بشري: نتخطى needs_help=1 / is_closed=1 / auto_reply_hold_until
    في المستقبل.
  - حد أقصى للإرسال في كل تشغيل (MAX_SENDS_PER_RUN) حتى لا نتجاوز timeout.

Usage:
    from religious_hajj_3msg_followup import run
    result = run(agent, payload)   # payload: {dry_run: bool, limit: int}
"""

import os
import sys
import json
import re
import sqlite3
import logging
import threading
from datetime import datetime, timedelta

from fts_paths import get_data_path

# =============================================================================
# ثوابت السير العمل
# =============================================================================
# الإعلانات الأربعة المستهدفة حصرياً (شرط التفعيل من الجذور)
TARGET_AD_IDS = [
    "120248310136460757",
    "120248557092680757",
    "120248587975700757",
    "120247657321100757",
]

# القسم الديني فقط — فلترة صارمة صفرية (ممنوع أي قسم آخر في هذا الـ workflow)
TARGET_LOCATION = "Religious"

# قاعدة بيانات المحادثات (نفس مسار chat_db)
DB_FILE = get_data_path("chat_history.db")

# ملف الحالة المحلي (قاعدة النظام G: يُمنع agent.load_state/save_state)
STATE_FILE = get_data_path("religious_hajj_3msg_followup_state.json")

# عتبات التوقيت بالساعات (مقاسة من آخر رسالة حقيقية للعميل)
STAGE1_HOURS = 1.0          # فولو أب ١: بعد ساعة
STAGE2_HOURS = 8.0          # فولو أب ٢: بعد ٨ ساعات
STAGE3_HOURS = 22.0         # فولو أب ٣: بعد ٢٢ ساعة (قبل قفل النافذة بساعتين — أمان)
WINDOW_HOURS = 24.0         # نافذة Meta الكاملة: لا إرسال بعدها نهائياً (خطأ Meta #10)

# حد أقصى للإرسال في كل تشغيل (حتى لا يتجاوز timeout الـ http_request)
MAX_SENDS_PER_RUN = 20

log = logging.getLogger("ReligiousHajj3MsgFollowup")

# بادئات الرسائل التي ليست رداً حقيقياً (تُستثنى من حساب "آخر رسالة عميل / آخر رد فريق"):
#   [Facebook Ad Referral]/[Facebook Referral] → رسالة إحالة تلقائية (ليست تفاعل عميل)
#   [System Log]/[System]/[SYSTEM] → سجلات نظام
#   [PROPOSED_DRAFT] → مسودة AI للموظف (لم تُرسل للعميل)
#   [ESCALATE] → إشعار تحويل نظامي
#   [AUTO] → سجل إجراء تلقائي
_NON_REAL_PREFIXES = (
    "[Facebook Ad Referral]",
    "[Facebook Referral]",
    "[System Log]",
    "[System]",
    "[SYSTEM]",
    "[PROPOSED_DRAFT]",
    "[ESCALATE]",
    "[AUTO]",
)

# =============================================================================
# نصوص الرسائل الثلاث (كما وردت من المدير حرفياً — لا تغيير ولا إعادة صياغة)
# =============================================================================
MSG_FOLLOWUP_1 = (
    "اطمنا إن تفاصيل البرامج والأسعار وصلتك 🕋\n"
    "ومعظم اللي بيوصلهم التفاصيل بيبقى عندهم سؤال أو اتنين قبل ما ياخدوا القرار — "
    "عن السداد، أو الفنادق، أو مواعيد السفر، أو الفرق بين البرامج او تقدم في السياحه "
    "احسن ولا الداخليه ولا الجمعيات.\n"
    "\n"
    "اكتبلنا سؤالك هنا — أي سؤال — وهنجاوبك فورًا .\n"
    "ولو حابب اكلم حضرتك واشرحلك صوتي، ابعتلنا رقم الواتساب."
)

MSG_FOLLOWUP_2 = (
    "⚠️ معلومة مهمة لازم تعرفها قبل ٢٧ أغسطس:\n"
    "\n"
    "التقديم في حج ١٤٤٨ قناة واحدة بس — يعني اللي يقدّم في قرعة الداخلية "
    "(بتقفل الخميس ٢٧/٨) أو حج الجمعيات (بيقفل ٣١/٨) مش هيقدر يقدّم في الحج "
    "السياحي خالص السنة دي.\n"
    "\n"
    "وفرص القبول في الحج السياحي أعلى بكتير من القرعة — لأن الأعداد المتقدمة أقل بكتير.\n"
    "\n"
    "ومسجّلين الاهتمام معانا دلوقتي مبلغ الخصم متثبت باسمهم مهما كانت أسعار "
    "الضوابط الجديدة — يعني التسجيل المبكر مش مجرد أولوية، ده تثبيت فعلي.\n"
    "\n"
    "فقبل ما تحجز مكانك في أي قناة، اسألنا الأول — رد بأي سؤال وفريقنا هيوضحلك "
    "الفرق بالأرقام.\n"
    "\n"
    "FTS للسياحة — ترخيص وزارة السياحة فئة (أ) رقم ٢٠٨٩"
)

MSG_FOLLOWUP_3 = (
    "دي آخر رسالة نقدر نبعتهالك النهارده 🙏\n"
    "\n"
    "وقبل ما نسيبك، حاجتين كنا حابين يوصلوك:\n"
    "\n"
    "🎁 أي حد بيقدّم معانا في قرعة الحج السياحي بيدخل تلقائيًا سحب على ٣ عمرات "
    "مجانية + سحب تاني على تذكرة طيران أو العبّارة مجانًا\n"
    "\n"
    "🔒 واللي بيسجل قبل نزول ضوابط ١٤٤٨ مبلغ الخصم وأولوية مكانه بيتثبتوا باسمه .\n"
    "\n"
    "📱 ابعتلنا رقم تليفونك دلوقتي — وهتواصل معاك ، هجاوبك على أي سؤال، وبثبتلك "
    "ميزتك في دقيقة — من غير أي التزام.\n"
    "\n"
    "ولو عندك سؤال معين واقفك عن القرار، اكتبه مع الرقم وهنجاوبك عليه في أول رسالة."
)

# =============================================================================
# أدوات الوقت (توقيت القاهرة — قاعدة النظام F)
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
if not hasattr(sys, "_religious_hajj_3msg_followup_state_lock"):
    sys._religious_hajj_3msg_followup_state_lock = threading.Lock()
_STATE_LOCK = sys._religious_hajj_3msg_followup_state_lock


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
                if getattr(e, "errno", None) not in (5, 13, 22):
                    break
    if last_err is not None:
        log.error(f"Failed to save state: {last_err}")


def _hold_active(hold_until, now) -> bool:
    """هل فترة إيقاف الرد الآلي (auto_reply_hold_until) ما زالت سارية؟"""
    if not hold_until:
        return False
    d = _parse_dt(hold_until)
    return bool(d and d > now)


def _is_non_real(text: str) -> bool:
    """هل الرسالة ليست تفاعلاً حقيقياً (إحالة/سجل/مسودة)؟"""
    t = str(text or "")
    return t.startswith(_NON_REAL_PREFIXES)


# =============================================================================
# استعلامات قاعدة البيانات (فلترة صارمة من الجذور — قاعدة النظام 15)
# =============================================================================
def _get_ad_conversations(cursor):
    """المحادثات الواردة من الإعلانات الأربعة فقط وفي قسم Religious فقط.
    الفلترة تتم في SQL من الجذور (facebook_ad_id IN ... AND location = 'Religious')
    وليس برمجياً — ممنوع جلب أي بيانات من أقسام أخرى.
    """
    qmarks = ",".join("?" * len(TARGET_AD_IDS))
    cursor.execute(
        f"""
        SELECT chat_id, sender_identifier, contact_name, source, location,
               receiving_phone_id, last_message_time, needs_help, is_closed,
               auto_reply_hold_until, customer_phone
        FROM conversations
        WHERE facebook_ad_id IN ({qmarks})
          AND location = ?
          AND (is_deleted IS NULL OR is_deleted = 0)
          AND last_message_time IS NOT NULL
        -- نرتب الأقدم أولاً (ASC) بحيث تُعالج المحادثات الأقرب لإغلاق نافذة
        -- مراحلها قبل الأحدث، فلا تُحرم رسالة المرحلة 3 بسبب MAX_SENDS_PER_RUN
        -- عند وجود تراكم (Backlog).
        ORDER BY last_message_time ASC
        """,
        (*TARGET_AD_IDS, TARGET_LOCATION),
    )
    rows = cursor.fetchall()
    return [dict(r) for r in rows] if rows else []


def _last_customer_message(cursor, chat_id):
    """
    آخر رسالة حقيقية أرسلها العميل (توقيت العد الأساسي لنافذة الـ 24 ساعة).
    نستبعد رسائل الإحالة/السجلات ([Facebook Ad Referral]...) لأنها ليست تفاعلاً
    حقيقياً من العميل. أما رسائل الميديا (صوت/فيديو/صورة) فهي رد حقيقي → تُبقي
    المرساة سليمة.
    """
    cursor.execute(
        """
        SELECT text, timestamp
        FROM messages
        WHERE chat_id = ? AND sender_type = 'customer'
        ORDER BY timestamp DESC
        LIMIT 20
        """,
        (chat_id,),
    )
    for row in cursor.fetchall():
        text, ts = str(row[0] or ""), row[1]
        if _is_non_real(text):
            continue
        return text, ts
    return None, None


def _last_agent_reply(cursor, chat_id):
    """
    آخر رد حقيقي من الفريق/الـ agent (يُستثنى من البادئات غير الحقيقية مثل
    [PROPOSED_DRAFT] و[System Log] — فلا نظن أن الفريق رد وهو لم يرد).
    """
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
        if _is_non_real(text):
            continue
        return text, ts
    return None, None


# =============================================================================
# منطق المراحل (كلها مقاسة من آخر رسالة حقيقية للعميل)
# =============================================================================
def _target_stage(elapsed_h: float):
    """المرحلة المستحقة بناءً على الساعات المنقضية من آخر رسالة للعميل."""
    if elapsed_h < STAGE1_HOURS:
        return None
    if elapsed_h < STAGE2_HOURS:
        return 1
    if elapsed_h < STAGE3_HOURS:
        return 2
    if elapsed_h < WINDOW_HOURS:
        return 3
    return None  # النافذة انغلقت — ممنوع الإرسال (خطأ Meta #10)


def _stage_message(stage: int) -> str:
    if stage == 1:
        return MSG_FOLLOWUP_1
    if stage == 2:
        return MSG_FOLLOWUP_2
    return MSG_FOLLOWUP_3


# =============================================================================
# الإرسال
# =============================================================================
def _send_message(agent, conv: dict, text: str, dry_run: bool = False):
    """إرسال الرسالة عبر القناة الصحيحة (Facebook / WhatsApp) وتسجيلها في السجل."""
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


# =============================================================================
# الدالة الرئيسية (يستدعيها محرك الأتمتة)
# =============================================================================
def run(agent, payload: dict = None) -> dict:
    """
    نقطة الدخول التي يستدعيها محرك الأتمتة (run_script).

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
    stats = {"started": 0, "stopped_customer_replied": 0, "stopped_agent_replied": 0,
             "window_closed": 0, "skipped_human_handling": 0}

    try:
        conn = sqlite3.connect(DB_FILE, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    except Exception as e:
        msg = f"Failed to connect to DB: {e}"
        log.error(f"[ReligiousHajj3Msg] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}

    state = _load_state()
    chats = state.setdefault("chats", {})

    try:
        conversations = _get_ad_conversations(cursor)
        log.info(f"[ReligiousHajj3Msg] Found {len(conversations)} conversations "
                 f"from ads {TARGET_AD_IDS} in location '{TARGET_LOCATION}'")

        for conv in conversations:
            chat_id = str(conv.get("chat_id") or "").strip()
            if not chat_id:
                continue
            if limit and processed_chats >= limit:
                break

            # ===== لا نتداخل مع موظف بشري أو محادثة مغلقة =====
            try:
                if int(conv.get("needs_help") or 0) == 1:
                    stats["skipped_human_handling"] += 1
                    continue
            except Exception:
                pass
            try:
                if int(conv.get("is_closed") or 0) == 1:
                    stats["skipped_human_handling"] += 1
                    continue
            except Exception:
                pass
            if _hold_active(conv.get("auto_reply_hold_until"), now):
                stats["skipped_human_handling"] += 1
                continue

            entry = chats.get(chat_id)

            # ===== تحسين الأداء: تخطٍ سريع للمحادثات غير النشطة وغير المتتبعة =====
            # المحادثات غير المتتبعة (بدون سجل حالة) التي تجاوز نشاطها نافذة الـ
            # 24 ساعة لا يمكن مراسلتها إطلاقاً (نافذة Meta مغلقة) → نتخطاها من
            # الجذور دون أي استعلام إضافي على الرسائل.
            if entry is None:
                lmt = _parse_dt(conv.get("last_message_time"))
                if lmt is None or (now - lmt).total_seconds() / 3600.0 > WINDOW_HOURS:
                    continue

            # ===== حالة نهائية: اكتمل التسلسل أو أُوقف → لا نعيد =====
            if entry is not None and (entry.get("sequence_done") or entry.get("stopped")):
                processed_chats += 1
                continue

            # ===== لقطة المحادثة (استعلامان فقط لكل محادثة) =====
            last_customer_text, last_ts_raw = _last_customer_message(cursor, chat_id)
            if not last_ts_raw:
                continue
            last_customer_ts = _parse_dt(last_ts_raw)
            if last_customer_ts is None:
                continue

            _last_agent_text, last_agent_ts_raw = _last_agent_reply(cursor, chat_id)
            last_agent_ts = _parse_dt(last_agent_ts_raw)

            # ===== محادثة جديدة: تهيئة الحالة =====
            if entry is None:
                entry = {
                    "chat_id": chat_id,
                    "anchor": last_customer_ts.isoformat(),
                    "last_customer_reply": last_customer_ts.isoformat(),
                    "highest_stage_sent": 0,
                    "stages": {},
                    "updated_at": now_iso,
                }
                chats[chat_id] = entry

            # ===== قاعدة الإيقاف الفوري: العميل رد أثناء السلسلة → نقف فوراً =====
            # "لو العميل رد في أي وقت، السلسلة بتقف فورًا والنافذة بتتصفّر"
            # المرساة = آخر رسالة حقيقية للعميل. لو ظهرت رسالة عميل أحدث من آخر
            # متابعة أرسلناها → العميل تفاعل معنا → نوقف السلسلة نهائياً لهذه
            # المحادثة (يتولى الفريق/الـ AI الرد عليه) ولا نرسل أي مرحلة لاحقة.
            prev_cust = _parse_dt(entry.get("last_customer_reply"))
            if prev_cust is not None and last_customer_ts > prev_cust:
                entry["last_customer_reply"] = last_customer_ts.isoformat()
                entry["last_customer_text"] = str(last_customer_text or "")[:200]
                entry["stopped"] = True
                entry["stopped_reason"] = "customer_replied"
                entry["updated_at"] = now_iso
                stats["stopped_customer_replied"] += 1
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                continue

            # لو لم نرسل أي مرحلة بعد (highest_stage_sent == 0) والـ agent/الفريق
            # رد حقيقياً بعد آخر رسالة العميل → لا نبدأ السلسلة أبداً (يوجد رد).
            highest = int(entry.get("highest_stage_sent") or 0)
            if highest == 0 and last_agent_ts is not None and last_agent_ts > last_customer_ts:
                entry["stopped"] = True
                entry["stopped_reason"] = "agent_replied"
                entry["updated_at"] = now_iso
                stats["stopped_agent_replied"] += 1
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                continue

            # ===== حساب الوقت المنقضي من آخر رسالة حقيقية للعميل =====
            elapsed_h = (now - last_customer_ts).total_seconds() / 3600.0
            entry["last_customer_reply"] = last_customer_ts.isoformat()
            entry["anchor"] = last_customer_ts.isoformat()

            # ===== نافذة الـ 24 ساعة انتهت: لا نرسل شيئاً ونُعلّم للوقاية =====
            if elapsed_h >= WINDOW_HOURS:
                if highest == 0:
                    # لم يبدأ التسلسل أبداً → حذف السجل من الحالة لصغر الملف
                    chats.pop(chat_id, None)
                else:
                    # اكتمل التسلسل أو النافذة انغلقت قبل المراحل → نمنع التكرار
                    entry["sequence_done"] = True
                    entry["updated_at"] = now_iso
                stats["window_closed"] += 1
                processed_chats += 1
                if not dry_run:
                    _save_state(state)
                continue

            # ===== المرحلة المستحقة =====
            target = _target_stage(elapsed_h)
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
                stats["started"] = stats.get("started", 0) + 1
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
            f"Sent {sent_count} follow-up message(s) with {len(errors)} error(s). "
            f"Stats: {stats}"
        )
        log.info(f"[ReligiousHajj3Msg] {message}")
        return {
            "ok": len(errors) == 0,
            "sent_count": sent_count,
            "errors": errors,
            "message": message,
            "stats": stats,
        }
    except Exception as e:
        msg = f"Error in run: {e}"
        log.error(f"[ReligiousHajj3Msg] {msg}")
        return {"ok": False, "sent_count": 0, "errors": [msg], "message": msg}
    finally:
        try:
            conn.close()
        except Exception:
            pass
