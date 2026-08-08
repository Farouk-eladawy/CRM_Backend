import json
s = """{
    "a": "b\ncd",
    "x": "y\\nz"
}"""
try:
    j = json.loads(s, strict=False)
    print(j)
except Exception as e:
    print("Error:", e)
