import json
import requests

try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    
    app_id = "1023237193740707"
    app_secret = config.get("facebook", {}).get("app_secret", "YOUR_APP_SECRET")
    
    # We can't query app mode without app secret easily, but we can check if it's development mode
    # Let's just ask the user directly since this is the most common cause.
except Exception as e:
    pass
