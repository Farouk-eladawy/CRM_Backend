import json
import requests

try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    page_token = config.get("facebook", {}).get("page_access_token")
    page_id = "134596153060573" # the page id from the webhook logs
    
    url = f"https://graph.facebook.com/v19.0/{page_id}/subscribed_apps"
    params = {"access_token": page_token}
    
    response = requests.get(url, params=params)
    print("Subscribed Apps for the Page:")
    print(json.dumps(response.json(), indent=2))
    
except Exception as e:
    print(f"Error: {e}")
