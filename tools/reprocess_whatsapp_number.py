import sqlite3
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python tools/reprocess_whatsapp_number.py <phone_digits>")
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
        SELECT chat_id, contact_name, receiving_phone_id, location, needs_help, auto_reply_hold_until, last_message_time
        FROM conversations
        WHERE sender_identifier = ?
        ORDER BY last_message_time DESC
        LIMIT 1
        """,
        (phone,),
    )
    conv = c.fetchone()
    if not conv:
        print("Conversation not found.")
        return 1

    chat_id = conv["chat_id"]
    name = conv["contact_name"] or "Customer"
    phone_id = conv["receiving_phone_id"]

    c.execute(
        """
        SELECT text, timestamp
        FROM messages
        WHERE chat_id = ?
          AND sender_type = 'customer'
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (chat_id,),
    )
    msg = c.fetchone()
    conn.close()
    if not msg or not (msg["text"] or "").strip():
        print("No customer message found to reprocess.")
        return 1

    body = str(msg["text"]).strip()

    print("Reprocessing chat_id:", chat_id)
    print("Location:", conv["location"])
    print("Customer:", name, phone)
    print("Phone ID:", phone_id)
    print("Last customer msg (first 220 chars):", body[:220].replace("\n", " "))

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from ai_agent import AIAgent

    agent = AIAgent()
    agent.process_whatsapp_message(
        sender_phone=phone,
        message_body=body,
        sender_name=name,
        phone_id=phone_id,
        timestamp=None,
        skip_db_save=True,
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
