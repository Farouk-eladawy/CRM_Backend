import requests
import json

url = "http://localhost:8080/message/sendText/fts_internal_notifications"
headers = {
    "apikey": "429683C4C977415CAAFCCE10F7D57E11",
    "Content-Type": "application/json"
}

target_employees = [
    "201027722684", # Abdelrahman Sayed
    "201129155520", # Ahmed Taha
    "201020711106"  # Hazem_Mohamed
]

for emp_phone in target_employees:
    payload = {
        "number": emp_phone,
        "text": f"🚨 *Test from Evolution API* 🚨\nTest message to {emp_phone} to verify cancellation workflow notifications."
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Sent to {emp_phone}: Status {response.status_code}")
        print(response.json())
    except Exception as e:
        print(f"Failed to send to {emp_phone}: {e}")
