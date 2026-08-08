import requests
import sqlite3

API_URL = "http://localhost:5001/api/operations/create_record"

conn = sqlite3.connect("airtable_mirror.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT table_name FROM mirror_tables WHERE base_label='religious' AND ignored=0")
tables = [r["table_name"] for r in c.fetchall()]

for t in tables:
    print(f"Testing table: {t}")
    payload = {
        "table_name": t,
        "fields": {
            "الاسم": f"تست تلقائي - {t}",
            "المدفوع": 50,
            "السعر": 150
        },
        "actor": {"username": "admin"}
    }
    res = requests.post(API_URL, json=payload)
    print(f"  Status: {res.status_code}")
    if res.status_code != 200:
        print(f"  Error: {res.text}")
