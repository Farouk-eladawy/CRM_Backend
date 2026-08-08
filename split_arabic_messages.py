import argparse
import re
import sqlite3
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="chat_history.db")
    parser.add_argument("--phone", required=True)
    args = parser.parse_args()

    arabic_re = re.compile(r"[\u0600-\u06FF]")

    with sqlite3.connect(args.db) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM conversations
            WHERE source=?
              AND sender_identifier=?
              AND (thread_id IS NULL OR thread_id=?)
            ORDER BY last_message_time DESC
            LIMIT 1
            """,
            ("WhatsApp", args.phone, ""),
        )
        orig = cur.fetchone()
        if not orig:
            raise SystemExit("No primary WhatsApp conversation found for phone")

        orig_chat_id = orig["chat_id"]

        cur.execute(
            "SELECT msg_id, text FROM messages WHERE chat_id=? ORDER BY timestamp ASC",
            (orig_chat_id,),
        )
        rows = cur.fetchall()
        move_ids = [r["msg_id"] for r in rows if arabic_re.search((r["text"] or ""))]

        if not move_ids:
            print("No Arabic messages found. Nothing to move.")
            return

        new_chat_id = str(uuid.uuid4())
        last_time = str(orig["last_message_time"] or "")
        new_thread_id = (
            ("split_arabic_" + last_time.replace(":", "").replace("-", "").replace(".", "").replace("T", "_"))[:64]
            if last_time
            else "split_arabic"
        )
        receiving_phone_id = (
            str(orig["receiving_phone_id"])
            if "receiving_phone_id" in orig.keys() and orig["receiving_phone_id"] is not None
            else ""
        )
        location = str(orig["location"] or "Unknown")
        contact_name = str(orig["contact_name"] or "Guest") + " (Split)"

        sender_identifier_to_use = args.phone
        try:
            cur.execute(
                """
                INSERT INTO conversations (
                    chat_id, source, sender_identifier, contact_name, airtable_record_id,
                    last_message_time, location, thread_id, receiving_phone_id, sales_inbox
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, 0)
                """,
                (new_chat_id, "WhatsApp", sender_identifier_to_use, contact_name, "", location, new_thread_id, receiving_phone_id),
            )
        except sqlite3.IntegrityError:
            sender_identifier_to_use = f"{args.phone}_split_arabic"
            cur.execute(
                """
                INSERT INTO conversations (
                    chat_id, source, sender_identifier, contact_name, airtable_record_id,
                    last_message_time, location, thread_id, receiving_phone_id, sales_inbox
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, 0)
                """,
                (new_chat_id, "WhatsApp", sender_identifier_to_use, contact_name, "", location, new_thread_id, receiving_phone_id),
            )

        cur.executemany(
            "UPDATE messages SET chat_id=? WHERE msg_id=?",
            [(new_chat_id, mid) for mid in move_ids],
        )

        for cid in (orig_chat_id, new_chat_id):
            cur.execute("SELECT MAX(timestamp) FROM messages WHERE chat_id=?", (cid,))
            mx = cur.fetchone()[0]
            if mx:
                cur.execute("UPDATE conversations SET last_message_time=? WHERE chat_id=?", (mx, cid))

        conn.commit()

        print(f"Moved {len(move_ids)} message(s)")
        print(f"Original chat_id: {orig_chat_id}")
        print(f"New chat_id: {new_chat_id}")
        print(f"New sender_identifier: {sender_identifier_to_use}")
        print(f"New thread_id: {new_thread_id}")


if __name__ == "__main__":
    main()
