import sqlite3
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python tools/link_whatsapp_chat_by_phone.py <phone_digits>")
        return 2

    phone = str(argv[1]).strip()
    if not phone:
        print("Missing phone.")
        return 2

    conn = sqlite3.connect("chat_history.db", timeout=15.0)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        """
        SELECT chat_id, sender_identifier, contact_name, airtable_record_id, location, last_message_time
        FROM conversations
        WHERE sender_identifier = ?
          AND lower(source) = 'whatsapp'
        ORDER BY last_message_time DESC
        LIMIT 1
        """,
        (phone,),
    )
    conv = c.fetchone()
    conn.close()
    if not conv:
        print("Conversation not found.")
        return 1
    if conv["airtable_record_id"]:
        print("Already linked:", conv["airtable_record_id"])
        return 0

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from ai_agent import AIAgent
    import chat_db
    from airtable_fields import FieldIds

    agent = AIAgent()
    booking_record = agent.find_booking_by_contact(phone=phone)
    if not booking_record or not booking_record.get("id"):
        print("No booking found in Airtable for this phone.")
        return 1

    booking_nr_val = None
    try:
        booking_nr_val = agent.get_field_value(booking_record.get("fields", {}) or {}, FieldIds.BOOKING_NR)
    except Exception:
        booking_nr_val = None

    chat_db.update_conversation_info(
        chat_id=conv["chat_id"],
        airtable_record_id=booking_record["id"],
        booking_number=booking_nr_val,
        location=conv["location"],
    )
    print("Linked:", booking_record["id"], "booking_nr:", booking_nr_val or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

