import json
import re

def _clean_json_text(s):
    txt = str(s or "").strip()
    if "```json" in txt:
        txt = txt.split("```json", 1)[1]
    elif "```" in txt:
        txt = txt.split("```", 1)[1]
    if "```" in txt:
        txt = txt.split("```", 1)[0]
    return txt.strip()

def _extract_json_like_text(raw_text):
    cleaned = _clean_json_text(raw_text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start:end + 1]
    return cleaned

with open('pi_sessions/pi-hard-case-ahmady-case-context-20260711-052611-01859abd.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    last_line = lines[-1]
    data = json.loads(last_line)
    text = data["message"]["content"][1]["text"] # the assistant's text
    
    # This is what _run_pi_cli returns as "output"
    raw_output = text
    
    extracted = _extract_json_like_text(raw_output)
    try:
        parsed = json.loads(extracted, strict=False)
        print("Success! Parsed keys:", parsed.keys())
    except Exception as e:
        print("Failed to parse:", e)
        print("Extracted string:", repr(extracted[:100]))
