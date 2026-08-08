import sqlite3

def check_chat():
    db = sqlite3.connect('chat_history.db')
    db.row_factory = sqlite3.Row
    c = db.cursor()
    
    chat_id = "8cd61d3f-95ed-4ff4-8a33-92dbd8a30c97"
    
    print("\n--- Last 5 Messages ---")
    c.execute("SELECT sender_type, text, timestamp FROM messages WHERE chat_id=? ORDER BY timestamp DESC LIMIT 5", (chat_id,))
    for msg in c.fetchall():
        print(f"[{msg['timestamp']}] {msg['sender_type']}: {msg['text'][:100]}")

if __name__ == '__main__':
    check_chat()