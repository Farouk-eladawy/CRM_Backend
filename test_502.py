import requests

resp = requests.post("http://127.0.0.1:5001/api/chats/send", json={
    "chat_id": "test",
    "text": "test",
    "reply_channel": "facebook"
})

print(resp.status_code)
print(resp.text)
