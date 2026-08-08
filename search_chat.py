import sqlite3
import json

db_path = 'chat_history.db'
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

booking_num = 'GYG32L3YBBMM'

print(f"--- Searching for Booking Number: {booking_num} ---")

# Search in conversations
try:
    cursor.execute("SELECT * FROM conversations WHERE booking_number LIKE ? OR chat_id LIKE ? OR contact_name LIKE ?", 
                   (f'%{booking_num}%', f'%{booking_num}%', f'%{booking_num}%'))
    convs = [dict(row) for row in cursor.fetchall()]
    
    if convs:
        print(f"\nFound {len(convs)} conversation(s):")
        for conv in convs:
            print(f"- Chat ID: {conv.get('chat_id')}, Source: {conv.get('source')}, Name: {conv.get('contact_name')}")
            
            # Fetch messages for this chat_id
            cursor.execute("SELECT sender_type, text, timestamp FROM messages WHERE chat_id = ? ORDER BY timestamp ASC", (conv['chat_id'],))
            msgs = cursor.fetchall()
            print(f"  Messages ({len(msgs)}):")
            for msg in msgs:
                print(f"  [{msg[2]}] {msg[0]}: {msg[1]}")
            print("-" * 50)
    else:
        print("\nNo conversations found in SQLite.")
except Exception as e:
    print("Error querying conversations:", e)

# Also search raw text in messages just in case
try:
    cursor.execute("SELECT chat_id, sender_type, text, timestamp FROM messages WHERE text LIKE ? ORDER BY timestamp ASC", (f'%{booking_num}%',))
    msgs = cursor.fetchall()
    if msgs:
        print(f"\nFound {len(msgs)} message(s) containing the booking number in the text:")
        for msg in msgs:
            print(f"[{msg[3]}] Chat: {msg[0]} | {msg[1]}: {msg[2]}")
except Exception as e:
    pass
