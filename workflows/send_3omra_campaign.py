# -*- coding: utf-8 -*-
"""
send_3omra_campaign.py
=======================
حملة إرسال تمبلت واتساب "3omra" من رقم FTS Travels Hajj
(Phone Number ID: 1214164541774422 — رقم الواتساب +201094728015 — قسم Religious)
إلى قائمة أرقام محددة (263 رقم فريد) من طلب المدير.

- التمبلت: 3omra (اللغة en) — WABA Religious — تمت الموافقة عليه 2026-08-22
  * المكونات: HEADER (صورة) + BODY (نص ثابت بدون متغيرات) + زر QUICK_REPLY ("معاكم بأذن الله")
- صورة الهيدر: مرفوعة على Cloudinary لضمان رابط ثابت:
  https://res.cloudinary.com/dqlurfwet/image/upload/v1787426756/whatsapp_templates/3omra_header.png
- الإرسال: Meta Cloud API عبر agent.send_whatsapp_message
- المحادثات تُنشأ/تُحدَّث في chat_history.db (source=WhatsApp, location=Religious)
- جميع المحادثات تُخصص للمستخدم محمد سامي (user_id=15 / Mohamed_Sami)
  حتى يرد عليها هو فقط من لوحة التحكم (lead_owner_user_id='15').
- الأرقام تُوحَّد (إزالة + ومسافات وشرطات) وتُزال التكرارات قبل الإرسال
  (كل رقم يستلم الرسالة مرة واحدة فقط) حسب طلب المدير.

طريقة التشغيل (بدون إعادة تشغيل السيرفر):
    POST http://127.0.0.1:5001/api/automation/run_script
    {"script_name": "send_3omra_campaign.py", "payload": {"dry_run": true}}   # محاكاة
    {"script_name": "send_3omra_campaign.py"}                                 # إرسال فعلي
"""

import os
import re
import time
import logging
from datetime import datetime

log = logging.getLogger("send_3omra_campaign")

# =============================================================================
# قائمة الأرقام (من طلب المدير — بدون تكرار، كل رقم مرة واحدة فقط)
# =============================================================================
TARGET_PHONES = [
    "201036796862", "201222872106", "201114396080", "201150366968", "201201916097", "201224653577", "201002994629", "201005438449",
    "201001864204", "201026027949", "201119929596", "201286728817", "201004135119", "201273474752", "201128555116", "201159629700",
    "201007831055", "201093446939", "201061868904", "201146781562", "201123433889", "201004656276", "201222721015", "201033849222",
    "201022239090", "201157066670", "201025281508", "201063772377", "201210584820", "201095367454", "201003542516", "201200340323",
    "201118861995", "201033665966", "201147152426", "201062077075", "201027700980", "201225894068", "201112917866", "201005217645",
    "201123480468", "201201369970", "201008032363", "201124223004", "201030437270", "201130781950", "201147668430", "201005039168",
    "201001915832", "201066121110", "201208606207", "201009825560", "201111399026", "201069953733", "201068004415", "201129309625",
    "201101108900", "201023272329", "201122868767", "201123081072", "201000074565", "201555436383", "201227945305", "201115192386",
    "201287412996", "201147798853", "201007339130", "201006086499", "201271752524", "201004671506", "201003480894", "201221633408",
    "201275151674", "201123158404", "201060738598", "201113930180", "201003200429", "201000720744", "201114790349", "201003889065",
    "201159601044", "201147176464", "201027078848", "201223729654", "201228691221", "201009511896", "201003616287", "201006526368",
    "201006608908", "201212445534", "201001422216", "201006559421", "201001258069", "201120486635", "201150202088", "201155240971",
    "201095630979", "201068236999", "201018150374", "201001987004", "201229681131", "201228012573", "201507562567", "201114532779",
    "201007061436", "201221944366", "201158294104", "201005553770", "201099311996", "201034698446", "201002030435", "201003890036",
    "201227343588", "201000044026", "201101988178", "201202555583", "201147483401", "201271370688", "201003304010", "201226908389",
    "201111138666", "201006087052", "201148355658", "201004386096", "201223581396", "201144572761", "201207000936", "201021369928",
    "201060475751", "201029766558", "201110464474", "201145693601", "201159432209", "201000091926", "201222487700", "201221595657",
    "201157455263", "201091815404", "201096386029", "201145132692", "201090803803", "201005430020", "201006246013", "201017587968",
    "201006303146", "201008431713", "201010398717", "201226931705", "201227327787", "201001439400", "201098803896", "201224086766",
    "201001691643", "201282442555", "201006618792", "201111703552", "201012311371", "201064408499", "201211165224", "201119264686",
    "201033994501", "201013850333", "201001121165", "201065049178", "201055135095", "201143068577", "201001305330", "201020877805",
    "201091113531", "201004021122", "201033814126", "201005472629", "201119843496", "201005259757", "201000326251", "201159883944",
    "201229680001", "201006628824", "201050024769", "201115442422", "201158777358", "201004598738", "201142002652", "201142213367",
    "201126434640", "201014801928", "201007476697", "201069020343", "201092284483", "201111274890", "201091831636", "201000575790",
    "201272258879", "201001290551", "201001814645", "201023412500", "201099170994", "201117037945", "201226653808", "201115561225",
    "201019598578", "201221484821", "201069936698", "201007986828", "201006080160", "201093036433", "201271744880", "201119904514",
    "201091987428", "201118028444", "201115610007", "201228183496", "201223969696", "201226282400", "201555338628", "201003832531",
    "201228949685", "201093983340", "201050662192", "201000875659", "201121332177", "201211154253", "201014395609", "201005425428",
    "201068779340", "201016542992", "201000108112", "201006118233", "201002586564", "201030098267", "201001770298", "201104909737",
    "201021163990", "201149992444", "201142038588", "201008854881", "201127143576", "201129948875", "201003503997", "201001059370",
    "201033434440", "201095651517", "201011066139", "201032423547", "201065141467", "201000065713", "201096392397", "201002505396",
    "201270022731", "201099984490", "201067702626", "201117187333", "201028256484", "201148269822", "201515210588", "201004806906",
    "201093062608", "201028088448", "201122215008", "201003709000", "201097741504", "201227732265", "201007953274",
]

RECEIVING_PHONE_ID = "1214164541774422"   # FTS Travels Hajj (Religious) = +201094728015
TEMPLATE_NAME = "3omra"
TEMPLATE_LANGUAGE = "en"
LOCATION = "Religious"

# صورة هيدر التمبلت (مرفوعة على Cloudinary — رابط ثابت)
HEADER_MEDIA_URL = "https://res.cloudinary.com/dqlurfwet/image/upload/v1787426756/whatsapp_templates/3omra_header.png"
HEADER_MEDIA_TYPE = "image"

# المستخدم المخصص للحملة: محمد سامي (قسم Religious) — هو الوحيد القادر على الرد
OWNER_USER_ID = "15"
OWNER_USERNAME = "Mohamed_Sami"
OWNER_NAME = "Mohamed Sami"


def _clean_phone(v) -> str:
    """توحيد شكل الرقم: إزالة + والمسافات والشرطات، مع تحويل 0xxxxxxxxxx إلى 20xxxxxxxxxx."""
    c = "".join(ch for ch in str(v or "") if ch.isdigit())
    if not c:
        return ""
    if c.startswith("00"):
        c = c[2:]
    if c.startswith("0") and len(c) == 11:
        c = "20" + c[1:]
    elif c.startswith("1") and len(c) == 10:
        c = "20" + c
    return c


import threading
import sqlite3
from fts_paths import get_data_path

SENT_DB = get_data_path("send_3omra_campaign_sent.db")
_CAMPAIGN_LOCK = threading.Lock()
_CAMPAIGN_RUNNING = False

def _dedupe(phones):
    """إزالة التكرارات مع الحفاظ على الترتيب — كل رقم يستلم الرسالة مرة واحدة فقط."""
    seen = set()
    out = []
    for p in phones:
        c = _clean_phone(p)
        if not c or len(c) < 10:
            continue
        if c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _connect_sent_db():
    conn = sqlite3.connect(SENT_DB, timeout=30.0)
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sent_phones (
            phone TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            claimed_at TEXT,
            sent_at TEXT,
            error TEXT
        )
        """
    )
    return conn


def _seed_sent_from_chat_history():
    """Mark phones that already have a successful campaign log as sent."""
    try:
        import chat_db
        with sqlite3.connect(chat_db.DB_FILE, timeout=30.0) as chat_conn:
            chat_conn.execute("PRAGMA busy_timeout = 30000;")
            rows = chat_conn.execute(
                """
                SELECT DISTINCT c.sender_identifier
                FROM messages m
                JOIN conversations c ON c.chat_id = m.chat_id
                WHERE IFNULL(m.text, '') LIKE '[Campaign 3omra]%'
                  AND IFNULL(m.text, '') NOT LIKE '%FAILED%'
                  AND IFNULL(m.status, '') != 'error'
                """
            ).fetchall()
        now = datetime.utcnow().isoformat()
        with _connect_sent_db() as conn:
            for row in rows:
                phone = _clean_phone(row[0] if row else "")
                if not phone:
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO sent_phones (phone, status, claimed_at, sent_at)
                    VALUES (?, 'sent', ?, ?)
                    """,
                    (phone, now, now),
                )
            conn.commit()
    except Exception as e:
        log.warning("Could not seed 3omra sent ledger from chat history: %s", e)


def _claim_phone(phone: str) -> bool:
    """True if this run may send. False if already claimed/sent."""
    now = datetime.utcnow().isoformat()
    with _connect_sent_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO sent_phones (phone, status, claimed_at) VALUES (?, 'sending', ?)",
            (phone, now),
        )
        if cur.rowcount > 0:
            conn.commit()
            return True
        row = cur.execute("SELECT status FROM sent_phones WHERE phone = ?", (phone,)).fetchone()
        status = str((row or [""])[0] or "")
        if status == "failed":
            cur.execute(
                "UPDATE sent_phones SET status = 'sending', claimed_at = ?, error = NULL WHERE phone = ?",
                (now, phone),
            )
            conn.commit()
            return True
        conn.commit()
        return False


def _mark_phone(phone: str, status: str, error: str = None):
    now = datetime.utcnow().isoformat()
    with _connect_sent_db() as conn:
        if status == "sent":
            conn.execute(
                "UPDATE sent_phones SET status = 'sent', sent_at = ?, error = NULL WHERE phone = ?",
                (now, phone),
            )
        else:
            conn.execute(
                "UPDATE sent_phones SET status = ?, error = ? WHERE phone = ?",
                (status, str(error or "")[:400], phone),
            )
        conn.commit()


def _ensure_conversation(phone: str):
    """إنشاء/تحديث محادثة واتساب في chat_history.db وتخصيصها لمحمد سامي."""
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

    # التخصيص لمحمد سامي فقط (حتى تظهر المحادثة عنده في لوحة Religious)
    import sqlite3
    last_err = None
    for attempt in range(6):
        try:
            with sqlite3.connect(chat_db.DB_FILE, timeout=30.0) as conn:
                conn.execute("PRAGMA busy_timeout = 30000;")
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
        except sqlite3.OperationalError as e:
            last_err = e
            if "locked" not in str(e).lower() and "busy" not in str(e).lower():
                break
            time.sleep(0.25 * (attempt + 1))
        except Exception as e:
            last_err = e
            break
    log.warning("Owner assign skipped for %s after retries: %s", phone, last_err)
    return chat_id, None


def run(agent, payload: dict = None) -> dict:
    """
    نقطة الدخول — يستدعيها محرك الأتمتة /api/automation/run_script.
    payload اختياري:
      - phones: قائمة أرقام بديلة
      - dry_run: محاكاة فقط دون إرسال حقيقي
      - force: إعادة الإرسال حتى لو الرقم اتبعتله قبل كده (ممنوع إلا بأمر صريح)
      - max_sends: حد أقصى لعدد الإرسالات (للاختبار)
      - delay_sec: التأخير بين الرسائل (افتراضياً 2.5 ثانية — سياسة معدل الإرسال)
    """
    global _CAMPAIGN_RUNNING
    payload = payload or {}
    phones = _dedupe(payload.get("phones") or TARGET_PHONES)
    dry_run = bool(payload.get("dry_run", False))
    force = bool(payload.get("force", False))
    max_sends = int(payload.get("max_sends") or 0) or len(phones)
    delay_sec = float(payload.get("delay_sec") or 2.5)

    if not _CAMPAIGN_LOCK.acquire(blocking=False):
        return {
            "status": "error",
            "message": "campaign already running",
            "skipped": True,
        }
    if _CAMPAIGN_RUNNING:
        _CAMPAIGN_LOCK.release()
        return {
            "status": "error",
            "message": "campaign already running",
            "skipped": True,
        }
    _CAMPAIGN_RUNNING = True

    results = []
    sent_ok = 0
    sent_fail = 0
    skipped_already = 0
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if not dry_run:
            _seed_sent_from_chat_history()

        for idx, phone in enumerate(phones[:max_sends]):
            try:
                chat_id, err = _ensure_conversation(phone)
            except Exception as e:
                log.warning("ensure_conversation crashed for %s: %s", phone, e)
                results.append({"phone": phone, "status": "error", "step": "ensure_conversation", "error": str(e)})
                sent_fail += 1
                continue
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

            if not force and not _claim_phone(phone):
                skipped_already += 1
                results.append({
                    "phone": phone,
                    "status": "skipped_already_sent",
                    "chat_id": chat_id,
                    "template": TEMPLATE_NAME,
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
                    template_header_media_url=HEADER_MEDIA_URL,
                    template_header_media_type=HEADER_MEDIA_TYPE,
                )
            except Exception as e:
                ok = False
                meta = str(e)

            uncertain = bool(isinstance(meta, dict) and meta.get("uncertain"))
            if ok or uncertain:
                _mark_phone(phone, "sent")
            else:
                err_txt = ""
                if isinstance(meta, dict):
                    err_txt = str(meta.get("body") or meta.get("error") or "")[:400]
                else:
                    err_txt = str(meta or "")[:400]
                _mark_phone(phone, "failed", err_txt)

            # تسجيل محاولة الإرسال داخل المحادثة
            try:
                import chat_db
                body = ""
                if isinstance(meta, dict):
                    body = str(meta.get("body") or meta.get("error") or "")[:300]
                status_txt = "sent" if (ok or uncertain) else "error"
                header = f"[Campaign 3omra] Template '{TEMPLATE_NAME}'"
                if not ok:
                    header += f" FAILED - {body}" if not uncertain else " UNCERTAIN (not retried)"
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

            if ok or uncertain:
                sent_ok += 1
            else:
                sent_fail += 1
                body = ""
                if isinstance(meta, dict):
                    body = str(meta.get("body") or "")[:400]
                log.warning("Send failed for %s: %s", phone, body)

            results.append({
                "phone": phone,
                "status": "success" if ok else ("uncertain" if uncertain else "error"),
                "chat_id": chat_id,
                "template": TEMPLATE_NAME,
                "receiving_phone_id": RECEIVING_PHONE_ID,
                "owner": OWNER_NAME,
                "meta": meta if isinstance(meta, dict) else None,
            })

            if idx < len(phones[:max_sends]) - 1 and not dry_run:
                time.sleep(delay_sec)
                if (idx + 1) % 20 == 0:
                    log.info(f"Paused 5s after {idx + 1} sends (rate-limit guard)")
                    time.sleep(5)

        return {
            "status": "success",
            "data": {
                "script": "send_3omra_campaign.py",
                "run_at": now_str,
                "total_targeted": len(phones),
                "processed": len(results),
                "sent_ok": sent_ok,
                "sent_fail": sent_fail,
                "skipped_already_sent": skipped_already,
                "dry_run": dry_run,
                "template": TEMPLATE_NAME,
                "template_language": TEMPLATE_LANGUAGE,
                "receiving_phone_id": RECEIVING_PHONE_ID,
                "display_phone_number": "+201094728015",
                "header_media_url": HEADER_MEDIA_URL,
                "location": LOCATION,
                "owner_user_id": OWNER_USER_ID,
                "owner_name": OWNER_NAME,
                "results": results,
            },
        }
    finally:
        _CAMPAIGN_RUNNING = False
        try:
            _CAMPAIGN_LOCK.release()
        except Exception:
            pass
