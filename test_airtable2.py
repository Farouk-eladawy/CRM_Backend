import json, requests
try:
    config = json.load(open('config.json'))
    api_key = config['airtable']['api_key']
    base_id = config['airtable']['base_id']
    url = f'https://api.airtable.com/v0/{base_id}/Leads%20CRM'
    headers = {'Authorization': f'Bearer {api_key}'}
    res = requests.get(url, headers=headers, params={'maxRecords': 1})
    with open('test_output.txt', 'w') as f:
        f.write(str(res.status_code) + '\n' + res.text)
except Exception as e:
    with open('test_output.txt', 'w') as f:
        f.write(str(e))
