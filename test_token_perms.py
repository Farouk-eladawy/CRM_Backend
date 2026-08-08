import json
import requests

try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    page_token = config.get("facebook", {}).get("page_access_token")
    
    url = f"https://graph.facebook.com/v19.0/debug_token?input_token={page_token}&access_token={page_token}"
    response = requests.get(url)
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
