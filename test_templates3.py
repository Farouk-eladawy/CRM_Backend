import requests
import json

waba_id = "560373790489064"
access_token = "EAAPbtOBFAg0BOyf4WVThoNMNS0IbJ48aMtj1KOlPNtpMTQ3AofjA773YMu4364YCGTK37yipVoGdyBqE1VTtdBo5A9vqScBfG7vqzLDiluZC3E7qcyJCGbtP8rqHnxZCnns0gIvF4ZAuZC8GxdN6nL3umQipqfndpQKZCnp5TtXkmnweYh1efFtn4dFqIZBzw5kgZDZD"

url = f"https://graph.facebook.com/v19.0/{waba_id}/message_templates?access_token={access_token}&limit=50"
res = requests.get(url)
data = res.json().get('data', [])

for t in data:
    name = t.get('name')
    if name == 'ftstravels_confirm_payment':
        print(f"Language: {t.get('language')}")
        for c in t.get('components', []):
            print(f"Component: {c.get('type')}")
            print(f"Text: {c.get('text', '')}")
            if c.get('type') == 'BODY':
                text = c.get('text', '')
                import re
                param_matches = re.findall(r'\{\{(\d+)\}\}', text)
                expected = max([int(x) for x in param_matches]) if param_matches else 0
                print(f"  BODY vars: {expected}")
            if c.get('type') == 'HEADER':
                print(f"  HEADER format: {c.get('format')}")
            if c.get('type') == 'BUTTONS':
                for btn in c.get('buttons', []):
                    text = btn.get('text', '')
                    url = btn.get('url', '')
                    import re
                    param_matches = re.findall(r'\{\{(\d+)\}\}', text + url)
                    expected = max([int(x) for x in param_matches]) if param_matches else 0
                    print(f"  BUTTON vars: {expected} in {btn.get('type')}")
