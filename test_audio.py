import sqlite3
import os

db_path = "chat_history.db"
print(f"DB exists: {os.path.exists(db_path)}")

try:
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT chat_id FROM conversations WHERE airtable_record_id = 'reczhnYMTy1ipuizx' OR chat_id = 'reczhnYMTy1ipuizx'")
        row = c.fetchone()
        if row:
            chat_id = row[0]
            print(f"FOUND_CHAT_ID={chat_id}")
            
            # Now let's test sending to this chat_id
            import requests
            url = "http://127.0.0.1:5001/api/chats/send"
            data = {
                "chat_id": chat_id,
                "reply_channel": "auto",
                "text": "اختبار رسالة صوتية من النظام (Voice Note Test)"
            }
            try:
                with open("test_audio.ogg", "rb") as f:
                    files = {
                        "file": ("test_audio.ogg", f, "audio/ogg")
                    }
                    response = requests.post(url, data=data, files=files)
                    print("Status Code:", response.status_code)
                    print("Response:", response.text)
            except Exception as e:
                print(f"Error connecting to backend: {e}")
        else:
            print("CHAT_ID_NOT_FOUND")
except Exception as e:
    print(f"DB Error: {e}")