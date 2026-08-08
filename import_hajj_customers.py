# -*- coding: utf-8 -*-
"""
رفع عملاء حجوزات الحج (من شات الواتس) إلى قسم Religious CRM كـ Contacts.
- customer name  -> conversations.contact_name
- mobile number  -> conversations.customer_phone + sender_identifier
- tag            -> sales_customer_state.tags  (التصنيف)
- Assigned User  -> conversations.lead_owner_user_id + lead_owner_name (أقرب سيلز من عمود السيلز)
"""
import sys
import re
import uuid
import openpyxl
import chat_db

EXCEL = r"uploads/pi_attachments/session-e9bd5tl/d07b64e26b________________________________________2025.xlsx"

# تعيين أسماء السيلز في ملف الإكسل إلى مستخدمي النظام الفعليين (أقرب مطابقة)
SALES_MAP = {
    "احمد سيلز":        ("17", "أحمد خليل"),            # Ahmed_Khalil - أقرب أحمد في فريق Religious
    "هنادي":            ("1783096103617", "هنادي محمد"),  # Hanady_Mohamed
    "Abdalrhman📌":     ("1783096060057", "عبدالرحمن إبراهيم"),  # Abdelrhman_ibrahim
    "Ibrahim Elkhatib": ("8", "Ahmed_Elkhatib"),       # أحمد الخطيب - أقرب مطابقة لاسم عائلة Elkhatib
    "ملك":              ("1783096007121", "ملك ماهر"),  # Malak_Maher
    "شيماء حج":         None,                           # لا يوجد مستخدم مشابه -> تُترك فاضية
    "Aya Fts":          ("1783095968049", "أيه محمد"),  # Aya_Mohamed
    "احمد خليل":        ("17", "أحمد خليل"),            # Ahmed_Khalil
    "عبدالرحمن سيلز":   ("1783096060057", "عبدالرحمن إبراهيم"),  # Abdelrhman_ibrahim
    "ملك سيلز":         ("1783096007121", "ملك ماهر"),  # Malak_Maher
    "Mohamed Samy":     ("15", "محمد سامي"),            # Mohamed_Sami
    "Karim Alaa":       None,                           # لا يوجد مستخدم مشابه -> تُترك فاضية
}

def clean_phone(raw):
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s or "مش مكتوب" in s:
        return ""
    return re.sub(r"\D", "", s)

def load_rows():
    wb = openpyxl.load_workbook(EXCEL, data_only=True)
    ws = wb["كل الحجوزات"]
    rows = []
    for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or row[0] is None:
            continue
        name = str(row[2] or "").strip() if row[2] is not None else ""
        phone_raw = row[3]
        tag = str(row[5] or "").strip() if row[5] is not None else ""
        sales = str(row[6] or "").strip() if row[6] is not None else ""
        phone = clean_phone(phone_raw)
        rows.append({
            "excel_row": idx,
            "name": name,
            "phone_raw": str(phone_raw or "").strip() if phone_raw is not None else "",
            "phone": phone,
            "tag": tag,
            "sales": sales,
            "user": SALES_MAP.get(sales),
        })
    return rows

def main(dry_run=True):
    rows = load_rows()
    print(f"عدد الصفوف في ملف الإكسل: {len(rows)}")

    # منع التصادم: نفس الرقم يُستخدم لأكثر من عميل (أزواج / عائلات) -> معرّف فريد لكل صف
    used_senders = set()
    # فهرس الأرقام المستخدمة مسبقاً
    phone_usage = {}

    def make_sender(phone, name, row_no):
        if not phone:
            slug = re.sub(r"[^0-9A-Za-z\u0600-\u06FF]", "", name)[:30] or "unknown"
            base = f"manual_{slug}_{row_no}"
            return base
        cnt = phone_usage.get(phone, 0)
        phone_usage[phone] = cnt + 1
        if cnt == 0:
            return phone
        return f"{phone}_{cnt + 1}"

    stats = {"total": len(rows), "with_phone": 0, "no_phone": 0,
             "with_user": 0, "no_user": 0, "no_tag": 0, "created": 0}

    for r in rows:
        name = r["name"]
        phone = r["phone"]
        tag = r["tag"]
        user = r["user"]

        if phone:
            stats["with_phone"] += 1
        else:
            stats["no_phone"] += 1
        if user:
            stats["with_user"] += 1
        else:
            stats["no_user"] += 1
        if not tag:
            stats["no_tag"] += 1

        sender_id = make_sender(phone, name, r["excel_row"])

        if dry_run:
            continue

        try:
            conv = chat_db.get_or_create_conversation(
                source="Manual",
                sender_identifier=sender_id,
                contact_name=name,
                location="Religious",
                receiving_phone_id="",
            )
        except Exception as e:
            print(f"  [ERROR] row {r['excel_row']} ({name}): {e}")
            continue

        chat_id = conv["chat_id"]

        if phone:
            chat_db.update_conversation_info(chat_id, customer_phone=phone)

        if tag:
            chat_db.upsert_sales_state(chat_id=chat_id, updates={"tags": tag})

        if user:
            uid, uname = user
            chat_db.assign_sales_lead(chat_id, uid, uname)

        stats["created"] += 1

    print(f"\n=== {'DRY RUN' if dry_run else 'EXECUTED'} SUMMARY ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    from collections import Counter
    c = Counter(r["sales"] for r in rows)
    print("\nتوزيع السيلز في الملف:")
    for k, v in sorted(c.items(), key=lambda x: -x[1]):
        mapped = SALES_MAP.get(k)
        print(f"  {k!r}: {v}  ->  {mapped if mapped else '(فاضية - لا يوجد مطابق)'}")

    # عينات للتحقق
    print("\nعينات (أول 8 صفوف):")
    for r in rows[:8]:
        print(f"  row {r['excel_row']}: {r['name']} | {r['phone'] or 'بدون رقم'} | tag={r['tag']} | sales={r['sales']} -> {r['user']}")

if __name__ == "__main__":
    dry = True
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        dry = False
    main(dry_run=dry)
