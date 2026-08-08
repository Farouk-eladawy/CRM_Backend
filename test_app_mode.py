import json
import requests

try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    page_token = config.get("facebook", {}).get("page_access_token")
    
    # Check app status
    url = f"https://graph.facebook.com/v19.0/app?access_token={page_token}"
    response = requests.get(url)
    print(response.json())
except Exception as e:
    print(f"Error: {e}")
