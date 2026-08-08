import requests

API_URL = "http://localhost:5001/api/operations/create_record"

payload = {
    "table_name": "حجاج حج مباشر",
    "fields": {
        "الاسم": "تست",
        "المدفوع": 100,
        "السعر": 1000
    },
    "actor": {"username": "admin"}
}

response = requests.post(API_URL, json=payload)
print(response.status_code)
print(response.text)
