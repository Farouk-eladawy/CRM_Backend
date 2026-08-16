# -*- coding: utf-8 -*-
"""
Campaign: send Meta WhatsApp template "ahmed1" (Hajj 1448 – حصة حجاج الموسم الماضي)
from FTS Travels Hajj phone (Phone Number ID: 1214164541774422 - Religious WABA)
to a fixed list of numbers, then create/assign each conversation to Ahmed Khalil
(user id "17") so he can reply to the replies (lead_owner_user_id = '17').

Engineering notes (لماذا هذه البنية):
  - Pre-flight check: the template MUST be sendable from Meta. If the template is
    still PENDING (not approved), Meta returns #132001 "Template name does not exist
    in the translation" for EVERY language code, so we abort BEFORE sending to anyone
    and report clearly instead of mass-failing 25 sends.
  - Sends are direct Graph API calls (same endpoint ai_agent.send_whatsapp_message
    uses) so this works standalone WITHOUT touching ai_agent.py (rule: never modify
    ai_agent.py) and WITHOUT restarting the server (rule: no server restarts).
  - Conversations are created ONLY for numbers where Meta accepted the send (status
    "sent"), so we never create fake chats without a real message.
  - Assignment: chat_db.assign_sales_lead(chat_id, "17", "Ahmed Khalil") — same
    mechanism the shift router uses (lead_owner_user_id='17').
  - Rate limiting: 3s sleep between sends (Meta/Marketing best practice; avoids
    throttle/ban).
  - Duplicates in the list are sent only once (دقيق - لن نرسل لنفس الرقم مرتين).
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import chat_db

PHONE_NUMBER_ID = "1214164541774422"          # FTS Travels Hajj (Religious)
WABA_ID = "4487473721533334"                  # Religious WABA (template lives here)
TEMPLATE_NAME = "ahmed1"
TEMPLATE_LANGUAGE = "en"                      # اللغة المسجلة للتمبلت على ميتا
OWNER_USER_ID = "17"                          # أحمد خليل
OWNER_NAME = "Ahmed Khalil"
LOCATION = "Religious"
GRAPH_VERSION = "v21.0"
SEND_DELAY_SECONDS = 3

# نفس نص التمبلت من ميتا (يُستخدم للتسجيل في قاعدة البيانات فقط)
TEMPLATE_TEXT = (
    "السلام عليكم ورحمة الله 🌙\n"
    "معاك احمد خليل من شركة اف تي اس للسياحة.\n"
    "حضرتك من حجاجنا الكرام اللي قدموا معانا في الحج الموسم اللي فات، وربنا ما كتبهاش المرة دي.. "
    "بس النية اللي نويتها لسه مكتوبة بإذن الله.\n"
    "عشان كده الشركة قررت السنة دي تخصص حصة كاملة من أماكن حج ١٤٤٨ لحجاجنا اللي قدموا معانا "
    "الموسم الماضي — وبخصومات مميزه.\n"
    "يعني مكان حضرتك محجوز مبدئياً.. القرار بس بقى عندك.\n"
    "تحب أبعتلك برامج السنة دي والأسعار بعد الخصم؟ 🤲"
)

# قائمة الأرقام كما أرسلها المدير (26 إدخال، 25 فريد — 201001628232 مكرر مرة واحدة)
RAW_NUMBERS = [
    "+201004411417",
    "+201112755213",
    "+201019304511",
    "+201157066670",
    "+201229681131",
    "+201004671506",
    "+201156795434",
    "+201002030435",
    "+201226908389",
    "+201001987004",
    "+201001628232",
    "+201001628232",  # duplicate in manager's list - sent once
    "+201112349131",
    "+201001691643",
    "+201004386096",
    "+201277757942",
    "+201155333483",
    "+201097954056",
    "+201150065696",
    "+201064475109",
    "+201224404458",
    "+201272700897",
    "+201014875549",
    "+201094546724",
    "+201120055770",
    "+201023246311",
]


def clean_phone(p):
    """E.164 بدون علامة + وبلا مسافات (مثال: 201004411417)."""
    digits = re.sub(r"\D", "", str(p or ""))
    return digits


def local_phone(e164):
    """تحويل الرقم للصيغة المصرية المحلية 0XXXXXXXXXX للمطابقة مع المحادثات الموجودة."""
    d = clean_phone(e164)
    if d.startswith("20") and len(d) == 12:
        return "0" + d[2:]
    return d


def load_token():
    cfg = json.load(open("config.json", encoding="utf-8"))
    tok = (cfg.get("whatsapp") or {}).get("access_token") or ""
    if not tok:
        raise RuntimeError("Missing whatsapp.access_token in config.json")
    return tok


def meta_get(url, tok):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 200, json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace"))
        except Exception:
            body = {}
        return e.code, body


def meta_post(url, tok, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace"))
        except Exception:
            body = {}
        return e.code, body


def preflight_template(tok):
    """تحقق مبدئي: هل التمبلت معتمد وقابل للإرسال من هذا الرقم؟"""
    # 1) هل التمبلت موجود على الـ WABA؟ وما حالته؟
    url = (
        f"https://graph.facebook.com/{GRAPH_VERSION}/{WABA_ID}/message_templates"
        f"?name={TEMPLATE_NAME}&access_token={tok}"
    )
    code, data = meta_get(url, tok)
    if code != 200:
        return False, f"Could not list templates (HTTP {code}): {json.dumps(data, ensure_ascii=False)[:300]}"
    tmpls = data.get("data") or []
    if not tmpls:
        return False, f"Template '{TEMPLATE_NAME}' not found on WABA {WABA_ID}"
    statuses = {t.get("status") for t in tmpls}
    if "APPROVED" not in statuses:
        return (
            False,
            f"Template '{TEMPLATE_NAME}' is NOT approved for sending. "
            f"Current status(es): {sorted(statuses)}. Meta only allows sending APPROVED templates.",
        )

    # 2) محاولة إرسال حقيقية لرقم اختبار للتحقق أن الترجمة تُحل (يُرجع 404 لو مش متاح)
    url_send = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": "201001000000",
        "type": "template",
        "template": {"name": TEMPLATE_NAME, "language": {"code": TEMPLATE_LANGUAGE}},
    }
    code, body = meta_post(url_send, tok, payload)
    # لو نجح (200/201) أو حتى رفض بسبب رقم غير مسجل (131030) => التمبلت قابل للإرسال
    err_code = ""
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        err_code = str((body.get("error") or {}).get("code") or "")
    if code in (200, 201):
        return True, "template sendable (test accepted)"
    if err_code in ("131030", "131026", "132000"):
        # 131030 = recipient not in allowlist (عادي لو تفعيل اختبار) -> التمبلت نفسه سليم
        # 131026 = out of session
        # 132000 = param mismatch (يعني التمبلت موجود وقابل للإرسال لكن باراميترز ناقصة)
        return True, f"template sendable (test hit code {err_code} which is not a template-missing error)"
    if err_code == "132001":
        return False, (
            f"Template '{TEMPLATE_NAME}' cannot be sent: Meta says the translation does not exist "
            f"yet (code 132001). This happens while the template status is PENDING — it becomes "
            f"sendable only after Meta approval."
        )
    return True, f"unexpected test result HTTP {code} {json.dumps(body, ensure_ascii=False)[:300]}"


def send_one(tok, phone):
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {"name": TEMPLATE_NAME, "language": {"code": TEMPLATE_LANGUAGE}},
    }
    code, body = meta_post(url, tok, payload)
    msg_id = None
    if code in (200, 201) and isinstance(body, dict):
        msgs = body.get("messages") or []
        if msgs:
            msg_id = (msgs[0] or {}).get("id")
    return code, body, msg_id


def find_existing_conversation(phone):
    """
    ابحث عن محادثة موجودة بنفس الرقم (بالصيغة الدولية أو المحلية) حتى لا ننشئ
    مكررات — أرقام الكامبين دي موجودة فعلاً كمحادثات Religious (حجاج الموسم الماضي)
    مسجلة بالصيغة المحلية 0XXXXXXXXXX.
    """
    candidates = [clean_phone(phone)]
    loc = local_phone(phone)
    if loc != candidates[0]:
        candidates.append(loc)
    import sqlite3
    with sqlite3.connect(chat_db.DB_FILE, timeout=15.0) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        for ident in candidates:
            c.execute(
                "SELECT chat_id, contact_name, location, receiving_phone_id, lead_owner_user_id, lead_owner_name "
                "FROM conversations WHERE sender_identifier = ? ORDER BY last_message_time DESC LIMIT 1",
                (ident,),
            )
            row = c.fetchone()
            if row:
                return {"chat_id": row["chat_id"], "existing": True, "info": dict(row)}
    return None


def create_and_assign(phone, external_message_id):
    """
    إعادة استخدام المحادثة الموجودة (إن وجدت) أو إنشاء محادثة جديدة، ثم:
      - تحديث location إلى Religious و receiving_phone_id إلى رقم FTS Travels Hajj
      - تعيين المحادثة لأحمد خليل (17) حتى يرد على أي ردود من العملاء
      - تسجيل رسالة الإرسال في جدول messages
    """
    existing = find_existing_conversation(phone)
    chat_id = None
    contact_name = "Hajj Lead (Campaign ahmed1)"
    if existing:
        chat_id = existing["chat_id"]
        contact_name = existing.get("info", {}).get("contact_name") or contact_name

    if not chat_id:
        conv = chat_db.get_or_create_conversation(
            source="WhatsApp",
            sender_identifier=clean_phone(phone),
            contact_name=contact_name,
            location=LOCATION,
            receiving_phone_id=PHONE_NUMBER_ID,
        )
        chat_id = (conv or {}).get("chat_id") or (conv or {}).get("id")
        if not chat_id and isinstance(conv, dict):
            chat_id = conv.get("chat_id")
        if not chat_id:
            return {"ok": False, "error": "no_chat_id", "conv": str(conv)[:200]}

    # تحديث بيانات المحادثة (Religious + رقم الإرسال) لو كانت موجودة قديماً
    try:
        chat_db.update_conversation_routing(
            chat_id,
            location=LOCATION,
            receiving_phone_id=PHONE_NUMBER_ID,
        )
    except Exception:
        pass

    assign = chat_db.assign_sales_lead(chat_id, OWNER_USER_ID, OWNER_NAME)

    chat_db.add_message(
        chat_id=chat_id,
        sender_type="agent",
        text=f"[Sent WhatsApp] Template '{TEMPLATE_NAME}' sent (campaign ahmed1 - Hajj 1448)\n{TEMPLATE_TEXT}",
        status="sent",
        increment_unread=False,
        source="WhatsApp",
        external_message_id=external_message_id,
    )
    return {"ok": True, "chat_id": chat_id, "assign": assign, "reused_existing": bool(existing)}


def main():
    dry_run = "--dry-run" in sys.argv
    numbers = []
    seen = set()
    for raw in RAW_NUMBERS:
        p = clean_phone(raw)
        if not p:
            print(f"[SKIP] empty number: {raw!r}")
            continue
        if p in seen:
            print(f"[SKIP] duplicate number (sent once): {raw}")
            continue
        seen.add(p)
        numbers.append(p)

    print("=" * 70)
    print(f"Campaign: template '{TEMPLATE_NAME}' | phone id {PHONE_NUMBER_ID} | Religious")
    print(f"Targets: {len(numbers)} unique numbers (from {len(RAW_NUMBERS)} raw entries)")
    print("=" * 70)

    tok = load_token()

    ok, msg = preflight_template(tok)
    print(f"\n[PRE-FLIGHT] template '{TEMPLATE_NAME}': {msg}")
    if not ok:
        print("\n[ABORT] لم يتم إرسال أي رسالة. السبب:")
        print("  " + msg)
        print("\nملحوظة: بمجرد اعتماد التمبلت (APPROVED) من ميتا، أعد تشغيل نفس السكربت")
        print("  `python send_ahmed1_campaign.py` وسيرسل للجميع ويخصص المحادثات لأحمد خليل تلقائياً.")
        sys.exit(2)

    if dry_run:
        print("\n[DRY-RUN] لن يتم إرسال أي رسالة. الأرقام المستهدفة:")
        for i, p in enumerate(numbers, 1):
            print(f"  {i:>2}. {p}")
        return

    results = []
    for i, phone in enumerate(numbers, 1):
        code, body, msg_id = send_one(tok, phone)
        if code in (200, 201):
            info = create_and_assign(phone, msg_id)
            results.append({"phone": phone, "status": "sent", "message_id": msg_id, "assign": info})
            print(f"[{i:>2}/{len(numbers)}] SENT {phone} msg_id={msg_id} assign_ok={info.get('ok')}")
        else:
            err = body.get("error") if isinstance(body, dict) else body
            results.append({"phone": phone, "status": "failed", "code": code, "error": err})
            print(f"[{i:>2}/{len(numbers)}] FAILED {phone} HTTP {code}: {json.dumps(err, ensure_ascii=False)[:250]}")
        time.sleep(SEND_DELAY_SECONDS)

    sent = [r for r in results if r["status"] == "sent"]
    failed = [r for r in results if r["status"] == "failed"]
    print("\n" + "=" * 70)
    print(f"REPORT: sent={len(sent)} failed={len(failed)} total={len(results)}")
    for f in failed:
        print(f"  FAILED {f['phone']}: {f.get('code')} {json.dumps(f.get('error'), ensure_ascii=False)[:150]}")
    with open("ahmed1_campaign_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Full report saved to ahmed1_campaign_report.json")


if __name__ == "__main__":
    main()
