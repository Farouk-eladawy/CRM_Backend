import re
import sqlite3
import sys
from datetime import datetime, timedelta


DB_FILE = "chat_history.db"
CAIRO_OFFSET = timedelta(hours=3)


def norm_phone(s: str) -> str:
    return re.sub(r"[^0-9]", "", str(s or ""))


def safe_iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def parse_iso(s: str):
    try:
        return datetime.fromisoformat(str(s))
    except Exception:
        return None


def main(argv: list[str]) -> int:
    nums = argv[1:] or []
    if not nums:
        print("Usage: python tools/debug_whatsapp_autoreply.py <phone1> [phone2 ...]")
        return 2

    targets = {norm_phone(x) for x in nums if norm_phone(x)}
    if not targets:
        print("No valid phone digits provided.")
        return 2

    now_cairo = datetime.utcnow() + CAIRO_OFFSET

    conn = sqlite3.connect(DB_FILE, timeout=15.0)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("PRAGMA table_info(conversations)")
    conv_cols = {row[1] for row in c.fetchall()}
    has_hold = "auto_reply_hold_until" in conv_cols

    like_rows = []
    for t in targets:
        last6 = t[-6:] if len(t) >= 6 else t
        c.execute(
            """
            SELECT c.*,
                   (SELECT sender_type FROM messages m WHERE m.chat_id = c.chat_id ORDER BY timestamp DESC LIMIT 1) as last_sender_type,
                   (SELECT text FROM messages m WHERE m.chat_id = c.chat_id ORDER BY timestamp DESC LIMIT 1) as last_text,
                   (SELECT timestamp FROM messages m WHERE m.chat_id = c.chat_id ORDER BY timestamp DESC LIMIT 1) as last_msg_ts
            FROM conversations c
            WHERE REPLACE(REPLACE(REPLACE(c.sender_identifier,'+',''),' ',''),'-','') LIKE ?
            ORDER BY c.last_message_time DESC
            LIMIT 100
            """,
            (f"%{last6}%",),
        )
        like_rows.extend(c.fetchall())

    matched = []
    seen = set()
    for r in like_rows:
        chat_id = r["chat_id"]
        if chat_id in seen:
            continue
        seen.add(chat_id)
        sid = norm_phone(r["sender_identifier"])
        if sid in targets:
            matched.append(r)

    print(f"Now (Cairo): {safe_iso(now_cairo)}")
    print(f"Targets: {sorted(targets)}")
    print(f"Matched chats: {len(matched)}")

    for r in matched:
        chat_id = r["chat_id"]
        hold_until = r["auto_reply_hold_until"] if has_hold else None
        hold_dt = parse_iso(hold_until) if hold_until else None
        last_conv_dt = parse_iso(r["last_message_time"]) if r["last_message_time"] else None
        age_s = (now_cairo - last_conv_dt).total_seconds() if last_conv_dt else None

        print("\n--- CHAT ---")
        print("chat_id:", chat_id)
        print("source:", r["source"])
        print("sender_identifier:", r["sender_identifier"])
        print("location:", r["location"])
        print("needs_help:", r["needs_help"])
        print("unread_count:", r["unread_count"])
        if has_hold:
            print("auto_reply_hold_until:", hold_until)
            if hold_dt:
                print("hold_active_now:", now_cairo < hold_dt)
        print("last_message_time:", r["last_message_time"])
        if age_s is not None:
            print("age_seconds:", int(age_s))
        print("receiving_phone_id:", r["receiving_phone_id"] if "receiving_phone_id" in r.keys() else None)
        print("last_sender_type:", r["last_sender_type"])
        print("last_text:", (r["last_text"] or "")[:180].replace("\n", "\\n"))

        c.execute(
            "SELECT sender_type, text, timestamp, source, status FROM messages WHERE chat_id=? ORDER BY timestamp DESC LIMIT 12",
            (chat_id,),
        )
        msgs = [dict(x) for x in c.fetchall()]
        print("last_messages (newest first):")
        for m in msgs:
            print(
                f"  - {m.get('timestamp')} | {m.get('sender_type')} | {str(m.get('source') or '')} | {str(m.get('text') or '')[:140].replace(chr(10),' ')}"
            )

    conn.close()
    if not matched:
        print("\nNo exact match by normalized digits was found in conversations.sender_identifier.")
        print("Possible reasons:")
        print("- Number is stored differently (e.g., linked by airtable_record_id instead of sender_identifier).")
        print("- Conversation not created (webhook not received / DB not updated).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

