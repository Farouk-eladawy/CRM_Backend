import gmail_service

svc = gmail_service.GmailService(token_file='token.json', credentials_file='credentials.json')
threads = svc.service.users().threads().list(userId='me', q='GYGZGZXYNLWF').execute().get('threads', [])

for t in threads:
    thread = svc.service.users().threads().get(userId='me', id=t['id']).execute()
    for msg in thread.get('messages', []):
        if 'BRUNO Charlyne via GetYourGuide' in next((h['value'] for h in msg['payload']['headers'] if h['name'] == 'From'), ''):
            print(f"Message ID: {msg['id']}")
            print(f"Labels: {msg.get('labelIds', [])}")
            print(f"Date: {next((h['value'] for h in msg['payload']['headers'] if h['name'] == 'Date'), '')}")
