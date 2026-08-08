import json, requests
config = json.load(open('config.json'))
api_key = config['airtable']['api_key']
base_id = config['airtable']['base_id']
url = f'https://api.airtable.com/v0/{base_id}/Leads%20CRM'
headers = {'Authorization': f'Bearer {api_key}'}
res = requests.get(url, headers=headers, params={'maxRecords': 1})
print(res.status_code)
print(res.text)