import requests
import json
import time

url = "http://localhost:5001/webhook"
headers = {'Content-Type': 'application/json'}

# Using the page ID and a mock sender ID
payload = {
  "object": "page",
  "entry": [
    {
      "time": int(time.time() * 1000),
      "id": "134596153060573",
      "messaging": [
        {
          "sender": {
            "id": "27390547040601581"
          },
          "recipient": {
            "id": "134596153060573"
          },
          "timestamp": int(time.time() * 1000),
          "message": {
            "mid": "m_test_draft_123",
            "text": "عايز أعرف تفاصيل الحج الاقتصادي"
          }
        }
      ],
      "hop_context": {
        "app_id": 1023237193740707,
        "metadata": ""
      }
    }
  ]
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print("Status Code:", response.status_code)
print("Response:", response.text)
