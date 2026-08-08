import sqlite3

try:
    with sqlite3.connect('db/chat_history.db') as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id FROM conversations WHERE airtable_record_id = 'reczhnYMTy1ipuizx'")
        row = c.fetchone()
        if row:
            print(f"FOUND_CHAT_ID={row[0]}")
        else:
            print("CHAT_ID_NOT_FOUND_FOR_RECORD")
except Exception as e:
    print(f"DB Error: {e}")