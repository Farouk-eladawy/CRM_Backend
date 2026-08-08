import urllib.request
import json
import traceback

out_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\test_api_res.txt"

try:
    req = urllib.request.Request('http://127.0.0.1:5001/api/chats?limit=5')
    with urllib.request.urlopen(req) as response:
        data = response.read().decode('utf-8')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(data)
except Exception as e:
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(traceback.format_exc())
