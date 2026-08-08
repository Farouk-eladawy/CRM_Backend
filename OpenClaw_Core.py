import os
import json
import subprocess
import logging
import sys
import requests
from flask import Flask, request, jsonify, render_template # Added render_template
from flask_cors import CORS

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [OpenClaw Core] - %(message)s',
    handlers=[
        logging.FileHandler("system.log", mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
CORS(app) 

@app.after_request
def after_request(response):
    """Ensure CORS headers are present on all responses."""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# --- Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, 'tools')
LEARNING_DB_PATH = os.path.join(BASE_DIR, 'learning_db.json')

# Evolution API Config
EVOLUTION_API_URL = "http://localhost:8080" 
EVOLUTION_API_KEY = "global-api-key"
INSTANCE_NAME = "OpenClawInstance"

# Import AI Helper
sys.path.append(BASE_DIR)
try:
    from ai_helper import query_deepseek
except ImportError:
    logging.warning("⚠️ Could not import ai_helper. Falling back to rule-based logic.")
    query_deepseek = None

def run_tool(script_name, args):
    """Run a Python tool script and return output."""
    script_path = os.path.join(TOOLS_DIR, script_name)
    if not os.path.exists(script_path):
        return f"Error: Tool {script_name} not found."
    
    try:
        cmd = ["python", script_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        return result.stdout.strip()
    except Exception as e:
        return f"Error running tool: {e}"

def load_lessons():
    """Load past lessons from JSON DB."""
    if not os.path.exists(LEARNING_DB_PATH):
        return []
    try:
        with open(LEARNING_DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("lessons", [])
    except:
        return []

def find_relevant_lessons(message, lessons, limit=3):
    """Simple keyword-based retrieval of past lessons."""
    relevant = []
    message_words = set(message.lower().split())
    
    for lesson in lessons:
        context_words = set(lesson.get('context', '').lower().split())
        draft_words = set(lesson.get('ai_draft', '').lower().split())
        score = len(message_words.intersection(context_words)) * 2 + \
                len(message_words.intersection(draft_words))
        if score > 0:
            relevant.append((score, lesson))
            
    relevant.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in relevant[:limit]]

def generate_ai_response(message, relevant_lessons):
    """Generate response using AI with memory context."""
    if not query_deepseek:
        return "I am OpenClaw (Core). AI Module missing."

    memory_context = ""
    if relevant_lessons:
        memory_context = "### Past Lessons (Learn from these corrections):\n"
        for i, lesson in enumerate(relevant_lessons):
            memory_context += f"Lesson {i+1}:\n"
            memory_context += f"- Situation: {lesson.get('context')}\n"
            memory_context += f"- AI Draft (Bad): {lesson.get('ai_draft')}\n"
            memory_context += f"- Human Fix (Good): {lesson.get('human_final')}\n\n"
            
    system_prompt = (
        "You are OpenClaw, an intelligent travel assistant for FTS Travels.\n"
        "Your goal is to answer customer queries professionally and concisely.\n"
        "Critically important: Learn from the 'Past Lessons' provided below to match the human agent's style.\n"
        "If a past lesson shows a specific way to answer a similar question, mimic that style exactly.\n"
    )
    
    user_prompt = (
        f"{memory_context}\n"
        f"### Current User Message:\n{message}\n\n"
        "### Your Response:"
    )
    
    return query_deepseek(system_prompt, user_prompt)

def send_whatsapp_message(phone, text):
    """Send message back via Evolution API."""
    url = f"{EVOLUTION_API_URL}/message/sendText/{INSTANCE_NAME}"
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "number": phone,
        "options": {
            "delay": 1200,
            "presence": "composing",
            "linkPreview": False
        },
        "textMessage": {
            "text": text
        }
    }
    
    try:
        logging.info(f"📤 Sending WhatsApp to {phone} via Evolution API...")
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            logging.info("✅ Message sent successfully.")
            return True
        else:
            logging.error(f"❌ Failed to send WhatsApp: {response.text}")
            return False
    except Exception as e:
        logging.error(f"❌ Connection Error to Evolution API: {e}")
        return False

def process_core_logic(user_id, message):
    """
    Central Logic for processing messages.
    """
    logging.info(f"⚙️ Processing Logic for {user_id}: {message}")
    
    # --- COMMAND MODE CHECK ---
    if message.startswith("/") or message.startswith("!") or message.startswith("CMD:"):
        logging.info("⚡ Processing as Command")
        command = message.replace("CMD:", "").strip()
        if command.startswith("/") or command.startswith("!"):
            command = command[1:] 
            
        if "how to" in command.lower() or "explain" in command.lower():
             return "I can explain that... (Knowledge retrieval placeholder)", True
        else:
             output = run_tool("execute_airtable_action.py", [command])
             if "Triggered Successfully" in output:
                 return "✅ Command Executed Successfully!\n" + output, False
             elif "Error" in output:
                 return "❌ Command Failed:\n" + output, False
             else:
                 return f"⚙️ Execution Result:\n{output}", False

    # --- CHAT / LEARNING MODE ---
    lessons = load_lessons()
    relevant_lessons = find_relevant_lessons(message, lessons)
    if relevant_lessons:
        logging.info(f"🧠 Recalled {len(relevant_lessons)} relevant lessons.")
    
    response_text = generate_ai_response(message, relevant_lessons)
    logging.info(f"🤖 Draft Response: {response_text}")
    return response_text, True

# --- Endpoints ---

@app.route('/')
def index():
    """Serve the Simulator Interface."""
    return render_template('index.html')

@app.route('/agent/message', methods=['POST'])
def handle_message():
    """Simulator Endpoint"""
    data = request.json
    user_id = data.get('user')
    message = data.get('message', '').strip()
    
    reply, is_draft = process_core_logic(user_id, message)
    
    return jsonify({
        "status": "success",
        "reply": reply,
        "draft_mode": is_draft
    })

@app.route('/webhook/evolution', methods=['POST'])
def handle_evolution_webhook():
    """Evolution API Webhook Endpoint"""
    try:
        data = request.json
        event_type = data.get('event')
        
        if event_type == 'messages.upsert':
            msg_data = data.get('data', {})
            key = msg_data.get('key', {})
            
            if key.get('fromMe'):
                return jsonify({"status": "ignored", "reason": "fromMe"}), 200
                
            remote_jid = key.get('remoteJid', '')
            phone = remote_jid.split('@')[0]
            
            message_content = msg_data.get('message', {})
            text = message_content.get('conversation') or \
                   message_content.get('extendedTextMessage', {}).get('text') or \
                   ""
            
            if not text:
                 return jsonify({"status": "ignored", "reason": "no_text"}), 200
                 
            logging.info(f"📨 WhatsApp Webhook from {phone}: {text}")
            
            reply, is_draft = process_core_logic(phone, text)
            send_whatsapp_message(phone, reply)
            return jsonify({"status": "processed"}), 200
            
    except Exception as e:
        logging.error(f"Webhook Error: {e}")
        return jsonify({"status": "error"}), 500

    return jsonify({"status": "ok"}), 200

@app.route('/agent/feedback', methods=['POST'])
def handle_feedback():
    """Endpoint for corrections."""
    data = request.json
    ai_draft = data.get('ai_draft')
    human_final = data.get('human_final')
    context = data.get('context', 'General')
    output = run_tool("learn_from_feedback.py", [ai_draft, human_final, context])
    return jsonify({"status": "learned", "output": output})

from pyairtable import Api

# ... (Configuration section) ...
# Airtable Configuration
AIRTABLE_API_KEY = "patxxxx" # Placeholder: Replace with env var or config
AIRTABLE_BASE_ID = "appxxxx" # Placeholder
AIRTABLE_TABLE_NAME = "Leads CRM" # Placeholder

@app.route('/api/airtable/records', methods=['GET'])
def get_airtable_records():
    """Proxy to get records from Airtable to Frontend."""
    try:
        # Check if we have credentials (loaded from config.json usually)
        config_path = os.path.join(BASE_DIR, 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                api_key = config.get('airtable', {}).get('api_key')
                base_id = config.get('airtable', {}).get('base_id')
                table_name = config.get('airtable', {}).get('tables', {}).get('main_list')
        else:
             return jsonify({"status": "error", "message": "Config missing"}), 500

        api = Api(api_key)
        table = api.table(base_id, table_name)
        # Get recent records
        records = table.all(sort=["-Last Modified"], max_records=50)
        return jsonify({"status": "success", "records": records})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/airtable/update', methods=['POST'])
def update_airtable_record():
    """Proxy to update a record in Airtable."""
    try:
        data = request.json
        record_id = data.get('id')
        fields = data.get('fields')
        
        config_path = os.path.join(BASE_DIR, 'config.json')
        with open(config_path, 'r') as f:
             config = json.load(f)
             api_key = config.get('airtable', {}).get('api_key')
             base_id = config.get('airtable', {}).get('base_id')
             table_name = config.get('airtable', {}).get('tables', {}).get('main_list')

        api = Api(api_key)
        table = api.table(base_id, table_name)
        
        table.update(record_id, fields)
        return jsonify({"status": "success", "message": "Updated"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/observer/insights', methods=['GET'])
def get_observer_insights():
    """Reads observer.log and extracts audit results for the dashboard."""
    log_path = os.path.join(BASE_DIR, 'observer.log')
    if not os.path.exists(log_path):
        return jsonify({"status": "error", "message": "Log file not found"}), 404
        
    insights = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "🧠 Audit Result:" in line:
                    parts = line.split("🧠 Audit Result:")
                    if len(parts) > 1:
                        timestamp = line.split(" - ")[0]
                        content = parts[1].strip()
                        insights.append({
                            "timestamp": timestamp,
                            "content": content
                        })
        # Return last 50 insights
        return jsonify({"status": "success", "insights": insights[-50:]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500




if __name__ == '__main__':
    port = 18789
    logging.info(f"🚀 OpenClaw Core running on port {port}")
    app.run(host='0.0.0.0', port=port)
