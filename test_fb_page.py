import json
import requests

config_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

page_access_token = config.get("facebook", {}).get("page_access_token")
page_id = config.get("facebook", {}).get("page_id")

url = f"https://graph.facebook.com/v19.0/{page_id}?fields=id,name&access_token={page_access_token}"
response = requests.get(url)

print(json.dumps(response.json(), indent=2))
