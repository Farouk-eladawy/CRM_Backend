import requests
import json

waba_id = "560373790489064"
access_token = "EAAPbtOBFAg0BOyf4WVThoNMNS0IbJ48aMtj1KOlPNtpMTQ3AofjA773YMu4364YCGTK37yipVoGdyBqE1VTtdBo5A9vqScBfG7vqzLDiluZC3E7qcyJCGbtP8rqHnxZCnns0gIvF4ZAuZC8GxdN6nL3umQipqfndpQKZCnp5TtXkmnweYh1efFtn4dFqIZBzw5kgZDZD"

url = f"https://graph.facebook.com/v19.0/{waba_id}/message_templates?access_token={access_token}&limit=50"
res = requests.get(url)
data = res.json().get('data', [])

for t in data:
    name = t.get('name')
    if name in ['pickup_time_new1', 'ftstravels_confirm_payment']:
        print(f"\nTemplate: {name}")
        for c in t.get('components', []):
            print(f"  {c.get('type')}")
            text = c.get('text', '')
            import re
            param_matches = re.findall(r'\{\{(\d+)\}\}', text)
            if param_matches:
                expected = max([int(x) for x in param_matches])
                print(f"    Expected vars: {expected}")
