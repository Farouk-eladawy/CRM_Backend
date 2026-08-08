import json
import requests

try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    page_token = config.get("facebook", {}).get("page_access_token")
    page_id = "134596153060573" # the page id from the webhook logs
    
    url = f"https://graph.facebook.com/v19.0/{page_id}/subscribed_apps"
    
    # We want to add message_echoes to the existing ones
    fields = "messages,messaging_postbacks,messaging_referrals,message_reads,message_deliveries,message_echoes"
    
    params = {
        "access_token": page_token,
        "subscribed_fields": fields
    }
    
    print(f"Updating subscriptions for page {page_id}...")
    response = requests.post(url, params=params)
    print("Response:", response.json())
    
    # Verify
    print("\nVerifying updated subscriptions...")
    verify_response = requests.get(url, params={"access_token": page_token})
    print(json.dumps(verify_response.json(), indent=2))
    
except Exception as e:
    print(f"Error: {e}")
