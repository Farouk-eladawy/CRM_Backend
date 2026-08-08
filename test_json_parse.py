import json
with open('pi_sessions/pi-hard-case-ahmady-case-context-20260711-052611-01859abd.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if "message" in data and "content" in data["message"]:
            for content in data["message"]["content"]:
                if content.get("type") == "text":
                    text = content["text"]
                    if "```json" in text:
                        jtext = text.split("```json")[1].split("```")[0].strip()
                        try:
                            json.loads(jtext, strict=False)
                            print("Valid JSON!")
                        except Exception as e:
                            print("Invalid JSON:", e)
                            print(repr(jtext[:100]))
