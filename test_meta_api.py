import requests
token = "EAAPbtOBFAg0BOyf4WVThoNMNS0IbJ48aMtj1KOlPNtpMTQ3AofjA773YMu4364YCGTK37yipVoGdyBqE1VTtdBo5A9vqScBfG7vqzLDiluZC3E7qcyJCGbtP8rqHnxZCnns0gIvF4ZAuZC8GxdN6nL3umQipqfndpQKZCnp5TtXkmnweYh1efFtn4dFqIZBzw5kgZDZD"
print(requests.get(f"https://graph.facebook.com/v20.0/565029450024439?access_token={token}").text)
print(requests.get(f"https://graph.facebook.com/v20.0/560373790489064?access_token={token}").text)
