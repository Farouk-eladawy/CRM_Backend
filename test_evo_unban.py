import urllib.request
import json
import sqlite3

def get_api_key():
    conn = sqlite3.connect('chat_history.db')
    c = conn.cursor()
    c.execute('SELECT value FROM user_settings WHERE key="internal_whatsapp_notifications_config"')
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0]).get("apiKey", "")
    return "429683C4C977415CAAFCCE10F7D57E11"

api_key = get_api_key()

base_url = "http://127.0.0.1:8080"
instance_name = "fts_internal_notifications"
to_phone = "201010323484"

url = f"{base_url}/message/sendText/{instance_name}"
payload = {
    "number": to_phone,
    "text": "تجربة جديدة بعد تأكيد فك الحظر عن الرقم. هل وصلت الرسالة الآن يا أستاذ أحمدي؟"
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"apikey": api_key, "Content-Type": "application/json"})

try:
    with urllib.request.urlopen(req, timeout=15) as response:
        print("Response:", response.read().decode('utf-8'))
except Exception as e:
    print("Error:", str(e))
