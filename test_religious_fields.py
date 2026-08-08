import json
import requests

def get_fields():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    api_key = config['airtable']['api_key']
    base_id = config['airtable'].get('religious_base_id')
    
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        for table in data.get('tables', []):
            if table['name'] == 'حجاج حج مباشر':
                print(f"Table: {table['name']}")
                for field in table['fields']:
                    print(f"  - {field['name']}")
    else:
        print(f"Error: {r.status_code} {r.text}")

get_fields()