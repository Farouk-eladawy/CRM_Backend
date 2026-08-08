import gmail_service

svc = gmail_service.GmailService(token_file='token.json', credentials_file='credentials.json')
threads = svc.service.users().threads().list(userId='me', q='GYGZGZXYNLWF').execute().get('threads', [])

for t in threads:
    history = svc.get_thread_history(t['id'])
    for msg in history:
        if 'BRUNO Charlyne via GetYourGuide' in msg['sender']:
            print(f"[{msg['date']}] From: {msg['sender']}")
            print("BODY:")
            print(msg['body'])
            print("="*80)
