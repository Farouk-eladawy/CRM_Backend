import requests
import json

url = "http://127.0.0.1:5000/chat"

# Using a new email to ensure clean context
payload = {
    "message": "عاوز معلومات عن رحلة الغردقة الأقصر",
    "email": "test_luxor_guest@example.com"
}

headers = {
    "Content-Type": "application/json"
}

try:
    print(f"Sending query: {payload['message']}")
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("\n--- AI Reply ---")
        print(data.get("reply"))
        print("----------------")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
