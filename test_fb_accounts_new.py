import json
import requests
import sys

page_access_token = "EAAOioPl0MaMBRwiZCVqZCjkglEjdpaPFGEvIIUdlKKbAo2A1cM6nDldS5QJTN2wayi2X6NpVjuccvbiMgNEG2vErJtri2YupcRkKXPYYuSylo24UMcnRkkPqZAuHRRodaywZBwbWDaK8ur1nqGdPrR24qVX2QSzqhZAV70GCTVjobUO98AieyDzlqeRnm9UW6jwZDZD"

url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={page_access_token}"
response = requests.get(url)

print(json.dumps(response.json(), indent=2))
