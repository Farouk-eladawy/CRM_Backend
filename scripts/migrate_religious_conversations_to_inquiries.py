import argparse
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from pyairtable import Api


RELIGIOUS_LEADS_TABLE = "استفسارات جديدة"
RELIGIOUS_BOOKING_TABLES = [
    "حجاج حج مباشر",
    "حجاج حج مباشر باقات",
    "حجاج حج قرعة",
    "حجاج تحسين",
    "حجاج بري",
    "حجاج كوكتيل",
    "إحصائيات البرامج",
]


def looks_like_email(value):
    text = str(value or "").strip()
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text))


def normalize_phone(value):
    digits = re.sub(r"\D+", "", str(value or ""))
    if 7 <= len(digits) <= 15:
        return digits
    return ""


def load_config(root_dir):
    with open(root_dir / "config.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


def fetch_record(table_api, record_id):
    try:
        return table_api.get(record_id)
    except Exception:
        return None


def latest_customer_message(conn, chat_id):
    row = conn.execute(
        """
        SELECT text
        FROM messages
        WHERE chat_id = ?
          AND sender_type = 'customer'
          AND COALESCE(text, '') <> ''
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (chat_id,),
    ).fetchone()
    if row and row[0]:
        return str(row[0]).strip()

    row = conn.execute(
        """
        SELECT text
        FROM messages
        WHERE chat_id = ?
          AND COALESCE(text, '') <> ''
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (chat_id,),
    ).fetchone()
    return str(row[0]).strip() if row and row[0] else ""


def build_target_rows(conn, leads_ids, list_ids, religious_leads_ids, religious_booking_ids, limit=None):
    rows = [
        dict(r)
        for r in conn.execute(
            """
            SELECT
                chat_id,
                source,
                sender_identifier,
                contact_name,
                airtable_record_id,
                booking_number,
                location,
                last_message_time
            FROM conversations
            WHERE lower(COALESCE(location, '')) = 'religious'
            ORDER BY last_message_time DESC
            """
        ).fetchall()
    ]

    targets = []
    for row in rows:
        record_id = str(row.get("airtable_record_id") or "").strip()
        if record_id in religious_leads_ids or record_id in religious_booking_ids:
            continue

        if not record_id:
            row["migration_reason"] = "missing_record_id"
            targets.append(row)
        elif record_id in leads_ids:
            row["migration_reason"] = "linked_to_leads_crm"
            targets.append(row)
        elif record_id in list_ids:
            row["migration_reason"] = "linked_to_main_list"
            targets.append(row)
        else:
            row["migration_reason"] = "unclassified_nonreligious_link"
            targets.append(row)

        if limit and len(targets) >= limit:
            break

    return targets


def choose_name(row, old_fields):
    current_name = str(row.get("contact_name") or "").strip()
    current_name_lower = current_name.lower()
    if current_name and current_name_lower != "guest" and not current_name_lower.startswith("facebook user"):
        return current_name

    for key in ("Customer Name", "الاسم"):
        candidate = str(old_fields.get(key) or "").strip()
        if candidate:
            return candidate
    return current_name or "Guest"


def choose_email(row, old_fields, allow_old_record_contact):
    sender_identifier = str(row.get("sender_identifier") or "").strip()
    if looks_like_email(sender_identifier):
        return sender_identifier

    if allow_old_record_contact:
        for key in ("Customer Email", "الايميل"):
            candidate = str(old_fields.get(key) or "").strip()
            if looks_like_email(candidate):
                return candidate
    return ""


def choose_phone(row, old_fields, allow_old_record_contact):
    source = str(row.get("source") or "").strip().lower()
    sender_identifier = str(row.get("sender_identifier") or "").strip()
    if source == "whatsapp":
        phone = normalize_phone(sender_identifier)
        if phone:
            return phone

    if allow_old_record_contact:
        for key in ("Customer Phone", "رقم التليفون"):
            phone = normalize_phone(old_fields.get(key))
            if phone:
                return phone
    return ""


def build_inquiry_fields(row, old_table_name, old_fields, message_text, allow_old_record_contact):
    booking_number = str(row.get("booking_number") or "").strip()
    detail_lines = []
    if message_text:
        detail_lines.append(message_text)
    if booking_number:
        detail_lines.append(f"Previous linked booking number: {booking_number}")
    inquiry_text = "\n".join(detail_lines).strip()

    notes_parts = [
        f"Migrated from conversation {row['chat_id']}",
        f"Previous table: {old_table_name or 'None'}",
        f"Previous record id: {str(row.get('airtable_record_id') or '').strip() or 'None'}",
        f"Source: {str(row.get('source') or '').strip() or 'Unknown'}",
    ]
    if booking_number:
        notes_parts.append(f"Previous booking number: {booking_number}")

    fields = {
        "الاسم": choose_name(row, old_fields),
        "النوع": "جديد",
        "تاريخ الاستفسار": str(row.get("last_message_time") or datetime.utcnow().isoformat()),
        "تم الانشاء بواسطة": "Religious Migration",
        "ملاحظات": " | ".join(notes_parts),
        "AI Chat Log": (
            f"[SYSTEM]: Migrated Religious conversation from {old_table_name or 'None'} "
            f"(old_record_id={str(row.get('airtable_record_id') or '').strip() or 'None'})"
        ),
    }

    email_value = choose_email(row, old_fields, allow_old_record_contact)
    phone_value = choose_phone(row, old_fields, allow_old_record_contact)
    if email_value:
        fields["الايميل"] = email_value
    if phone_value:
        fields["رقم التليفون"] = phone_value
    if inquiry_text:
        fields["ملاحظات أو تفاصيل الاستفسار"] = inquiry_text
    return fields


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    backup_dir = root_dir / "migration_backups"
    backup_dir.mkdir(exist_ok=True)

    config = load_config(root_dir)
    api = Api(config["airtable"]["api_key"])
    main_base_id = config["airtable"]["base_id"]
    religious_base_id = config["airtable"]["religious_base_id"]

    leads_table = api.table(main_base_id, "Leads CRM")
    list_table = api.table(main_base_id, "List")
    religious_leads_table = api.table(religious_base_id, RELIGIOUS_LEADS_TABLE)

    leads_ids = {record["id"] for record in leads_table.all()}
    list_ids = {record["id"] for record in list_table.all()}
    religious_leads_ids = {record["id"] for record in religious_leads_table.all()}

    religious_booking_ids = set()
    for table_name in RELIGIOUS_BOOKING_TABLES:
        religious_booking_ids.update(record["id"] for record in api.table(religious_base_id, table_name).all())

    conn = sqlite3.connect(root_dir / "chat_history.db")
    conn.row_factory = sqlite3.Row

    targets = build_target_rows(
        conn,
        leads_ids=leads_ids,
        list_ids=list_ids,
        religious_leads_ids=religious_leads_ids,
        religious_booking_ids=religious_booking_ids,
        limit=args.limit or None,
    )

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_payload = {
        "created_at_utc": datetime.utcnow().isoformat() + "Z",
        "target_count": len(targets),
        "targets": targets,
    }
    backup_path = backup_dir / f"religious_migration_backup_{timestamp}.json"
    backup_path.write_text(json.dumps(backup_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    migrated = []
    failed = []

    for row in targets:
        old_record_id = str(row.get("airtable_record_id") or "").strip()
        reason = row.get("migration_reason")
        old_table_name = None
        old_record = None

        if old_record_id in leads_ids:
            old_table_name = "Leads CRM"
            old_record = fetch_record(leads_table, old_record_id)
        elif old_record_id in list_ids:
            old_table_name = "List"
            old_record = fetch_record(list_table, old_record_id)
        elif old_record_id:
            old_table_name = "UNCLASSIFIED"

        old_fields = (old_record or {}).get("fields", {})
        message_text = latest_customer_message(conn, row["chat_id"])
        allow_old_record_contact = not old_record_id
        new_fields = build_inquiry_fields(
            row,
            old_table_name,
            old_fields,
            message_text,
            allow_old_record_contact,
        )

        try:
            new_record = religious_leads_table.create(new_fields, typecast=True)
            new_record_id = new_record["id"]
            conn.execute(
                """
                UPDATE conversations
                SET airtable_record_id = ?, booking_number = ?
                WHERE chat_id = ?
                """,
                (
                    new_record_id,
                    "" if old_record_id else str(row.get("booking_number") or ""),
                    row["chat_id"],
                ),
            )
            migrated.append(
                {
                    "chat_id": row["chat_id"],
                    "old_record_id": old_record_id,
                    "old_table_name": old_table_name,
                    "new_record_id": new_record_id,
                    "reason": reason,
                }
            )
        except Exception as exc:
            failed.append(
                {
                    "chat_id": row["chat_id"],
                    "old_record_id": old_record_id,
                    "old_table_name": old_table_name,
                    "reason": reason,
                    "error": str(exc),
                }
            )

    conn.commit()
    conn.close()

    result_payload = {
        "created_at_utc": datetime.utcnow().isoformat() + "Z",
        "backup_file": str(backup_path),
        "migrated_count": len(migrated),
        "failed_count": len(failed),
        "migrated": migrated,
        "failed": failed,
    }
    result_path = backup_dir / f"religious_migration_result_{timestamp}.json"
    result_path.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(
        {
            "backup_file": str(backup_path),
            "result_file": str(result_path),
            "migrated_count": len(migrated),
            "failed_count": len(failed),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
