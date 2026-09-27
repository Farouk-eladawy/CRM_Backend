import re
import sqlite3
from pathlib import Path

db = Path(__file__).resolve().parents[1] / "chat_history.db"
print("DB exists", db.exists(), db)
conn = sqlite3.connect(str(db), timeout=30)
conn.row_factory = sqlite3.Row
needles = [
    "201005138825",
    "201008841924",
    "201099405492",
    "1005138825",
    "1008841924",
    "1099405492",
]
rows = conn.execute(
    """
    SELECT chat_id, sender_identifier, contact_name, location, lead_owner_name,
           lead_owner_user_id, assigned_to, airtable_record_id, booking_number, is_deleted
    FROM conversations
    WHERE LOWER(COALESCE(source,'')) = 'whatsapp'
    """
).fetchall()
print("whatsapp chats", len(rows))
for r in rows:
    d = re.sub(r"\D", "", str(r["sender_identifier"] or ""))
    if any(n in d or (len(n) >= 9 and d.endswith(n[-9:])) for n in needles):
        print(dict(r))
