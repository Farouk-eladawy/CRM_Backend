import requests
import json

url = "http://127.0.0.1:5000/chat"

# Using a new email to ensure clean context
payload = {
    "message": "Tell me about the Orange Bay trip from Hurghada. Is lunch included?",
    "email": "test_user_orange_bay@example.com"
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
        
        # Also print booking info if any (should be None for new inquiry)
        print(f"Booking Found: {data.get('booking_found')}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
