import sys
import os
import requests
import json
from urllib.parse import quote
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from ai_agent import AIAgent
from airtable_fields import TABLE_NAME

agent = AIAgent()
base_url = f"https://api.airtable.com/v0/{agent.config['airtable']['base_id']}/{quote(TABLE_NAME)}?view={quote('Booking_Weekly')}"
headers = {"Authorization": f"Bearer {agent.config['airtable']['api_key']}"}

all_records = []
offset = None
pages = 0

while True:
    url = base_url
    if offset:
        # url += f"&offset={offset}" # What I did before
        url += f"&offset={quote(offset)}"
    
    print(f"Fetching page {pages+1} with URL: {url}")
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
        print("Error:", response.text)
        break
        
    data = response.json()
    records = data.get('records', [])
    all_records.extend(records)
    print(f"Got {len(records)} records. Total: {len(all_records)}")
    
    offset = data.get('offset')
    if not offset:
        break
    
    pages += 1
    if pages == 1:
        print("First record:", records[0]['fields'].get('Date Trip'))
    if pages > 5:
        print("Stopping at 5 pages.")
        break
