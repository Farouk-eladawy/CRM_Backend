import requests
import json
from ai_agent import AIAgent

agent = AIAgent()
base_id = agent.config["airtable"]["base_id"]
api_key = agent.config["airtable"]["api_key"]

res = requests.get(
    f"https://api.airtable.com/v0/{base_id}/List?view=Booking_tomorrow",
    headers={"Authorization": f"Bearer {api_key}"}
)

records = res.json().get('records', [])
print("Booking_tomorrow view dates:")
for r in records[:20]:
    print(r['fields'].get('Date Trip'))
