import json
import requests

try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    page_token = config.get("facebook", {}).get("page_access_token")
    customer_psid = "25879763984995048"
    
    url = f"https://graph.facebook.com/v19.0/{customer_psid}?fields=first_name,last_name,name&access_token={page_token}"
    
    response = requests.get(url)
    print(response.status_code)
    print(response.text)
except Exception as e:
    print(e)
