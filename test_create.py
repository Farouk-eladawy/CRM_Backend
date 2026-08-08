import requests

API_URL = "http://localhost:5001/api/operations/create_record"

payload = {
    "table_name": "حجاج حج مباشر",
    "fields": {
        "الاسم": "تست",
        "العميل": "تست عميل",
        "رقم الجواز": "12345",
        "رقم التاشيرة": "9876",
        "النوع": "ذكر",
        "نوع الحج": "معرفش",
        "تاريخ الذهاب": "2026-06-27",
        "السعر": 1000,
        "المدفوع": 100,
        "المتبقي": 900
    },
    "actor": {"username": "admin"}
}

response = requests.post(API_URL, json=payload)
print(response.status_code)
print(response.text)
