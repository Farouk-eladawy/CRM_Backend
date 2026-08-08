import requests

payload = {
    "entry": [{
        "changes": [{
            "value": {
                "metadata": {"phone_number_id": "565029450024439"},
                "messages": [{
                    "from": "201090005205",
                    "type": "text",
                    "text": {"body": "Test message via API"}
                }]
            }
        }]
    }]
}

resp = requests.post("https://api.ftstravels.com/webhook", json=payload)
print(resp.status_code, resp.text)
