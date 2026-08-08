import requests
import json

url = "http://127.0.0.1:5000/chat"

payload = {
    "message": "Do you provide diving suits?",
    "email": "newguest99@test.com"
}

headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print("--- AI Reply ---")
        print(data.get("reply"))
        print("----------------")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
