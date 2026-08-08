import urllib.request
import json
import sqlite3

def send_message():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('SELECT value FROM user_settings WHERE key="internal_whatsapp_notifications_config"')
    row = c.fetchone()
    conn.close()
    
    if not row:
        print("Config not found in DB")
        return
        
    cfg = json.loads(row[0])
    base_url = cfg.get("providerBaseUrl", "http://127.0.0.1:8080").rstrip("/")
    instance_name = cfg.get("instanceName", "fts_internal_notifications")
    api_key = cfg.get("apiKey", "")
    
    to_phone = "201010323484"
    
    url = f"{base_url}/message/sendText/{instance_name}"
    
    payload = {
        "number": to_phone,
        "text": "تجربة بعد مسح الرقم الجديد/المحدث. هل وصلت هذه الرسالة؟"
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"apikey": api_key, "Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            print("Send Response:", res_body)
    except Exception as e:
        print("Error sending message:", str(e))

if __name__ == "__main__":
    send_message()
