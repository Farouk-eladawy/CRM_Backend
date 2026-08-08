import requests
import json
from ai_agent import AIAgent

agent = AIAgent()
base_id = agent.config["airtable"]["base_id"]
api_key = agent.config["airtable"]["api_key"]

res = requests.get(
    f"https://api.airtable.com/v0/meta/bases/{base_id}/tables",
    headers={"Authorization": f"Bearer {api_key}"}
)

with open("airtable_meta.json", "w", encoding="utf-8") as f:
    json.dump(res.json(), f, indent=2)
