import requests

url = "http://localhost:8080/message/sendText/95C00886-267C-40AB-B553-4B8E22CDBBFB"
headers = {
    "apikey": "429683C4C977415CAAFCCE10F7D57E11",
    "Content-Type": "application/json"
}
payload = {
    "number": "201027722684",
    "text": "🚨 *Test from Evolution API* 🚨\nIf you receive this, the API works!"
}

response = requests.post(url, json=payload, headers=headers)
print(response.status_code)
print(response.text)
