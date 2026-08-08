import sqlite3

def find_error_10():
    db = sqlite3.connect('chat_history.db')
    c = db.cursor()
    
    print("Messages sent around 03:47:")
    c.execute("""
        SELECT m.chat_id, m.text, m.timestamp, c.source, c.contact_name, c.last_message_time 
        FROM messages m 
        JOIN conversations c ON m.chat_id = c.chat_id 
        WHERE m.sender_type='agent' AND m.timestamp LIKE '2026-07-20 03:47%'
    """)
    rows = c.fetchall()
    for r in rows:
        print(f"Chat ID: {r[0]}")
        print(f"Customer: {r[4]} | Source: {r[3]}")
        print(f"Time Sent: {r[2]}")
        print(f"Last Customer Message Time: {r[5]}")
        print(f"Text: {r[1][:100]}...")
        print("-" * 50)

if __name__ == '__main__':
    find_error_10()