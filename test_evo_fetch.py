import requests

url = "http://localhost:8080/instance/fetchInstances"
headers = {
    "apikey": "429683C4C977415CAAFCCE10F7D57E11"
}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.text)
