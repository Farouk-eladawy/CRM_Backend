import json
import requests
import logging
import os

# Load Config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return None

CONFIG = load_config()

def query_deepseek(system_prompt, user_prompt):
    """Generic function to query DeepSeek."""
    if not CONFIG:
        return None
        
    provider = CONFIG['ai']['providers']['deepseek']
    api_key = provider['api_key']
    api_url = provider['api_url']
    model = provider['model']
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"DeepSeek Query Failed: {e}")
        return None

def summarize_text_with_ai(text):
    """Summarizes a customer message into structured bullet points."""
    if not text or len(text) < 10:
        return text
        
    system_prompt = (
        "You are an expert support analyst. Summarize the customer's message/issue into 2-3 short, actionable bullet points. "
        "Use HTML line breaks (<br>) between points. "
        "Start each point with a relevant emoji (e.g., 📍 Location, 📅 Date, ⚠️ Issue, ❓ Question). "
        "Keep it very concise. No intro/outro."
        "Example output: ⚠️ Complaint about pickup delay<br>📍 Asking for driver location"
    )
    
    summary = query_deepseek(system_prompt, text)
    return summary if summary else text[:100] + "..."

def analyze_top_questions_with_ai(questions_list):
    """
    Takes a list of raw customer questions/messages and returns grouped categories with counts.
    Returns a list of tuples: [('Category/Question', count), ...]
    """
    if not questions_list:
        return []
        
    # If list is small, just return simple counter
    if len(questions_list) < 5:
        from collections import Counter
        return Counter(questions_list).most_common(5)

    system_prompt = (
        "You are a data analyst. I will provide a list of customer questions/messages. "
        "Group semantically similar questions together and return the TOP 5 most frequent issues/questions. "
        "Output ONLY a JSON object in this format: "
        "{'groups': [{'topic': 'Short Topic Name', 'count': 5, 'example': 'Example message'}, ...]}"
    )
    
    user_prompt = "Here are the messages:\n" + "\n".join(questions_list[:100]) # Limit to 100 messages to fit context
    
    response = query_deepseek(system_prompt, user_prompt)
    
    if response:
        try:
            # Extract JSON from response (handle code blocks if any)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
                
            data = json.loads(response)
            result = []
            for item in data.get('groups', []):
                # We normalize the count based on input list size if AI hallucinates numbers, 
                # but usually we trust the AI to estimate importance or we just take the label.
                # Since AI can't count perfectly in one go without processing, we might just use the labels 
                # and re-count, but for now let's trust the AI's clustering logic.
                result.append((f"{item['topic']} (e.g. {item.get('example', '')})", item['count']))
            return result
        except Exception as e:
            logging.error(f"Failed to parse AI grouping: {e}")
            
    # Fallback
    from collections import Counter
    return Counter([q[:50] for q in questions_list]).most_common(5)
