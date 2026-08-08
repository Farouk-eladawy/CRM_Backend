import json
import requests

config_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

app_id = config.get("facebook", {}).get("app_id")
app_secret = config.get("facebook", {}).get("app_secret")
page_access_token = config.get("facebook", {}).get("page_access_token")

url = f"https://graph.facebook.com/debug_token?input_token={page_access_token}&access_token={app_id}|{app_secret}"
response = requests.get(url)

print(json.dumps(response.json(), indent=2))
