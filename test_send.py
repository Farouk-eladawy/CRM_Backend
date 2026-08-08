import requests
import json

url = "http://127.0.0.1:5001/api/chats/send"
payload = {
    "chat_id": "af6fa3b7-6eb8-4556-96d7-e757cf2f3fae",
    "template_name": "ftstravels_confirm_payment",
    "template_language": "en"
}

try:
    res = requests.post(url, json=payload)
    print(res.status_code)
    print(res.text)
except Exception as e:
    print("Failed:", e)
