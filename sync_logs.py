import sqlite3
import os
import sys
import json
import requests

# Airtable Configuration
API_KEY = "pata59p87o7vQZcWJ.a5dbf97d3f8ccedbb874dd45a2777174e92a5d3511eb9c2c8f85f190e8c89c47"
BASE_ID = "appzc9rxT8kfD0HMp"
TABLE_NAME = "استفسارات جديدة"

def sync_missed_chat_logs():
    conn = sqlite3.connect('chat_history.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # نجلب المحادثات الحديثة التي لها Record ID في Airtable
    c.execute('''
        SELECT chat_id, airtable_record_id 
        FROM conversations 
        WHERE airtable_record_id LIKE 'rec%' 
        ORDER BY last_message_time DESC LIMIT 20
    ''')
    
    rows = c.fetchall()
    print(f"Found {len(rows)} recent conversations with Airtable IDs.")
    
    synced_count = 0
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    for row in rows:
        chat_id = row['chat_id']
        rec_id = row['airtable_record_id']
        
        c.execute('SELECT sender_type, text FROM messages WHERE chat_id = ? ORDER BY timestamp ASC', (chat_id,))
        messages = c.fetchall()
        
        if not messages:
            continue
            
        chat_log = []
        for m in messages:
            sender = 'Agent/System' if m['sender_type'] == 'agent' else 'Customer'
            text = m['text'] or ''
            chat_log.append(f"[{sender}]: {text}")
            
        full_log = "\n".join(chat_log)
        
        # محاولة تحديث Airtable مباشرة عبر الـ API
        url = f"https://api.airtable.com/v0/{BASE_ID}/{requests.utils.quote(TABLE_NAME)}/{rec_id}"
        payload = {
            "fields": {
                "AI Chat Log": full_log
            }
        }
        
        try:
            resp = requests.patch(url, json=payload, headers=headers)
            if resp.status_code == 200:
                print(f"✅ Successfully synced chat log to religious lead: {rec_id}")
                synced_count += 1
            else:
                # إذا لم يكن الـ Record موجوداً في هذا الجدول تحديداً سيتجاهله
                pass
        except Exception as e:
            pass

    conn.close()
    print(f"\\nFinished. Successfully updated {synced_count} records in Religious Leads table.")

if __name__ == "__main__":
    sync_missed_chat_logs()
