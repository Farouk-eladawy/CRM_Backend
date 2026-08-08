import sqlite3
import json

c = sqlite3.connect('chat_history.db')
c.row_factory = sqlite3.Row

rows = c.execute("SELECT timestamp, sender_type, text FROM messages WHERE chat_id = '8720707d-37b5-4d64-8a83-934cb9d8f058' ORDER BY timestamp DESC LIMIT 10").fetchall()
print("Recent messages in WhatsApp chat 8720707d (Booking GYG32L4W82KR):")
for r in rows:
    print(f"[{r['timestamp']}] {r['sender_type']}: {r['text'][:100]}...")
