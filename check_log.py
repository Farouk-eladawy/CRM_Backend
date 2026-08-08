import sqlite3

def check_recent_messages():
    db = sqlite3.connect('chat_history.db')
    c = db.cursor()
    print("Last 10 messages:")
    c.execute("SELECT chat_id, sender_type, text, timestamp FROM messages ORDER BY timestamp DESC LIMIT 10")
    for row in c.fetchall():
        print(row)

if __name__ == '__main__':
    check_recent_messages()
