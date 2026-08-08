import json
import os
import requests
import logging
from datetime import datetime, timedelta
import pytz
from pyairtable import Api
from collections import defaultdict, Counter
import cloudinary
import cloudinary.uploader
from report_template import generate_shift_html_report
from ai_helper import summarize_text_with_ai, analyze_top_questions_with_ai # Import AI Helper
from interaction_analyzer import analyze_interaction_type # Import New Analyzer
import re # Ensure regex is imported at top level

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')
WEBHOOK_URL = "https://hook.us2.make.com/hh1j7h7gbc3g1crf0gf6p9ve5darktqw"

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def setup_cloudinary():
    """Configure Cloudinary with hardcoded credentials (from ai_agent.py)."""
    try:
        cloudinary.config(
            cloud_name = "dqlurfwet",
            api_key = "676981699546932",
            api_secret = "gcy0eSAwFh6KDHpNa3NAa5bFvwI"
        )
        logging.info("Cloudinary configured.")
    except Exception as e:
        logging.error(f"Failed to configure Cloudinary: {e}")

def upload_html_to_cloudinary(html_content, filename="daily_report.html"):
    """Uploads HTML content to Cloudinary and returns the public URL."""
    try:
        # Save to temp file
        temp_path = os.path.join(SCRIPT_DIR, filename)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        logging.info(f"Uploading {filename} to Cloudinary...")
        # Upload using 'raw' resource type for HTML files to be accessible as-is
        response = cloudinary.uploader.upload(
            temp_path, 
            resource_type="raw", 
            public_id=f"reports/{datetime.now().strftime('%Y-%m-%d')}_report",
            overwrite=True
        )
        
        url = response.get("secure_url")
        logging.info(f"Upload successful: {url}")
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return url
    except Exception as e:
        logging.error(f"Cloudinary upload failed: {e}")
        return None

def load_config():
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load config: {e}")
        return None

def get_cairo_time():
    return datetime.now(pytz.timezone('Africa/Cairo'))

def determine_shift(dt_cairo):
    """
    Shift 1: 08:00 - 18:00
    Shift 2: 18:00 - 23:59:59
    Shift 3: 00:00 - 08:00
    """
    h = dt_cairo.hour
    if 8 <= h < 18:
        return "Shift 1 (Morning: 08:00 - 18:00)"
    elif 18 <= h <= 23:
        return "Shift 2 (Evening: 18:00 - 00:00)"
    else:
        return "Shift 3 (Night: 00:00 - 08:00)"

def is_sharm_booking(record_fields):
    """Check if the booking belongs to Sharm El Sheikh region."""
    # Field 'des' is usually the location/description
    des = str(record_fields.get('des', '')).lower()
    product_name = str(record_fields.get('Product name', '')).lower()
    
    keywords = ['sharm', 'sharm el sheikh', 'ssh']
    if any(k in des for k in keywords) or any(k in product_name for k in keywords):
        return True
    return False

def generate_html_report(stats, date_str):
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; border-left: 5px solid #e67e22; padding-left: 10px; }}
            h3 {{ color: #7f8c8d; margin-top: 20px; }}
            .summary-card {{ display: flex; gap: 20px; margin-bottom: 30px; }}
            .card {{ flex: 1; background: #ecf0f1; padding: 20px; border-radius: 8px; text-align: center; }}
            .card.highlight {{ background: #dff9fb; border: 1px solid #c7ecee; }}
            .card h4 {{ margin: 0 0 10px; color: #7f8c8d; font-size: 0.9em; text-transform: uppercase; }}
            .card .number {{ font-size: 2.5em; font-weight: bold; color: #2980b9; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f8f9fa; color: #2c3e50; }}
            .badge {{ padding: 5px 10px; border-radius: 15px; font-size: 0.8em; color: white; display: inline-block; }}
            .badge.success {{ background-color: #27ae60; }}
            .badge.draft {{ background-color: #f39c12; }}
            .badge.error {{ background-color: #c0392b; }}
            .sharm-section {{ background-color: #fff3e0; padding: 20px; border-radius: 8px; margin-top: 30px; border: 1px solid #ffe0b2; }}
            .footer {{ margin-top: 40px; text-align: center; font-size: 0.8em; color: #aaa; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 AI Agent Daily Report</h1>
            <p><strong>Date:</strong> {date_str} (Cairo Time)</p>
            
            <div class="summary-card">
                <div class="card highlight">
                    <h4>Total Processed</h4>
                    <div class="number">{stats['total_processed']}</div>
                </div>
                <div class="card">
                    <h4>Auto-Replied (Live)</h4>
                    <div class="number" style="color: #27ae60;">{stats['total_sent']}</div>
                </div>
                <div class="card">
                    <h4>Drafts (Human Review)</h4>
                    <div class="number" style="color: #f39c12;">{stats['total_drafts']}</div>
                </div>
            </div>

            <h2>🌍 Regional Breakdown</h2>
            
            <div class="sharm-section">
                <h3 style="color: #d35400;">🐫 Sharm El Sheikh (Employees 4 & 5)</h3>
                <table>
                    <tr><th>Metric</th><th>Count</th></tr>
                    <tr><td>Total Interactions</td><td>{stats['sharm']['total']}</td></tr>
                    <tr><td>Auto-Replied</td><td>{stats['sharm']['sent']}</td></tr>
                    <tr><td>Drafts Created</td><td>{stats['sharm']['drafts']}</td></tr>
                    <tr><td>Top Inquiries</td><td>{', '.join([f"{k} ({v})" for k,v in stats['sharm']['inquiries'].most_common(3)]) or 'None'}</td></tr>
                </table>
            </div>

            <h2>🕒 Shift Performance (General - Cairo/Hurghada)</h2>
            
            <h3>Shift 1 (08:00 - 18:00)</h3>
            <table>
                <tr><th>Metric</th><th>Count</th></tr>
                <tr><td>Processed</td><td>{stats['shift1']['total']}</td></tr>
                <tr><td>Replies / Drafts</td><td>{stats['shift1']['sent']} / {stats['shift1']['drafts']}</td></tr>
                <tr><td>Top Issues</td><td>{', '.join([f"{k} ({v})" for k,v in stats['shift1']['inquiries'].most_common(3)]) or 'None'}</td></tr>
            </table>

            <h3>Shift 2 (18:00 - 00:00)</h3>
            <table>
                <tr><th>Metric</th><th>Count</th></tr>
                <tr><td>Processed</td><td>{stats['shift2']['total']}</td></tr>
                <tr><td>Replies / Drafts</td><td>{stats['shift2']['sent']} / {stats['shift2']['drafts']}</td></tr>
                <tr><td>Top Issues</td><td>{', '.join([f"{k} ({v})" for k,v in stats['shift2']['inquiries'].most_common(3)]) or 'None'}</td></tr>
            </table>

            <h3>Shift 3 (00:00 - 08:00)</h3>
            <table>
                <tr><th>Metric</th><th>Count</th></tr>
                <tr><td>Processed</td><td>{stats['shift3']['total']}</td></tr>
                <tr><td>Replies / Drafts</td><td>{stats['shift3']['sent']} / {stats['shift3']['drafts']}</td></tr>
                <tr><td>Top Issues</td><td>{', '.join([f"{k} ({v})" for k,v in stats['shift3']['inquiries'].most_common(3)]) or 'None'}</td></tr>
            </table>

            <h2>🔥 Top Customer Inquiries (Global)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Inquiry Type</th>
                        <th>Count</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for inquiry, count in stats['global_inquiries'].most_common(10):
        html += f"<tr><td>{inquiry}</td><td>{count}</td></tr>"
        
    html += """
                </tbody>
            </table>
            
            <h2>📝 Drafts & Human Interventions</h2>
            <p>Below is a list of bookings where the AI prepared a draft for human review (and potential editing).</p>
            <table>
                <thead>
                    <tr>
                        <th>Booking Nr.</th>
                        <th>Customer Email</th>
                        <th>Inquiry Type</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    if stats['draft_details']:
        for draft in stats['draft_details']:
            html += f"<tr><td>{draft['booking_nr']}</td><td>{draft['email']}</td><td>{draft['inquiry']}</td></tr>"
    else:
        html += "<tr><td colspan='3' style='text-align:center;'>No drafts or human interventions recorded today.</td></tr>"

    html += """
                </tbody>
            </table>

            <div class="footer">
                Generated by FTS AI Agent System • Timezone: Africa/Cairo
            </div>
        </div>
    </body>
    </html>
    """
    return html

def main():
    config = load_config()
    if not config:
        return

    api_key = config['airtable']['api_key']
    base_id = config['airtable']['base_id']
    table_name = config['airtable']['tables']['main_list']

    logging.info("Connecting to Airtable...")
    api = Api(api_key)
    table = api.table(base_id, table_name)

    # Time window Determination
    now_cairo = get_cairo_time()
    
    # Logic:
    # If ~08:00 -> Report Shift 3 (Yesterday 00:00 - Today 08:00) 
    #   *Wait, Shift 3 is 00:00-08:00. So report covers Today 00:00 - 08:00.
    # If ~18:00 -> Report Shift 1 (Today 08:00 - 18:00)
    # If ~00:00 -> Report Shift 2 (Today 18:00 - 00:00)
    
    # We add 15 mins buffer in scheduling, so we check the current hour.
    hour = now_cairo.hour
    
    start_time = None
    end_time = None
    shift_label = "Unknown Shift"

    if 7 <= hour <= 9: # Run around 08:00
        # Report Night Shift (00:00 - 08:00 Today)
        start_time = now_cairo.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = now_cairo.replace(hour=8, minute=0, second=0, microsecond=0)
        shift_label = "Night Shift (00:00 - 08:00)"
        
    elif 17 <= hour <= 19: # Run around 18:00
        # Report Morning Shift (08:00 - 18:00 Today)
        start_time = now_cairo.replace(hour=8, minute=0, second=0, microsecond=0)
        end_time = now_cairo.replace(hour=18, minute=0, second=0, microsecond=0)
        shift_label = "Morning Shift (08:00 - 18:00)"
        
    elif 23 <= hour or hour <= 1: # Run around 00:00
        # Report Evening Shift (18:00 Today - 00:00 Tomorrow/Today End)
        # If we run at 00:05 (next day), we want Yesterday 18:00 to Yesterday 23:59
        if hour <= 1:
             # It is early morning next day, look back at yesterday
             yesterday = now_cairo - timedelta(days=1)
             start_time = yesterday.replace(hour=18, minute=0, second=0, microsecond=0)
             end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
             # Still same day (23:55), just capture until now
             start_time = now_cairo.replace(hour=18, minute=0, second=0, microsecond=0)
             end_time = now_cairo.replace(hour=23, minute=59, second=59, microsecond=999999)
             
        shift_label = "Evening Shift (18:00 - 00:00)"
    else:
        # Fallback for manual run: Last 12 hours
        logging.warning("Running outside standard shift times. Defaulting to last 12 hours.")
        end_time = now_cairo
        start_time = now_cairo - timedelta(hours=12)
        shift_label = f"Manual Run ({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')})"
    
    # Ensure start_time and end_time are offset-aware (Cairo)
    if start_time.tzinfo is None:
        start_time = pytz.timezone('Africa/Cairo').localize(start_time)
    if end_time.tzinfo is None:
        end_time = pytz.timezone('Africa/Cairo').localize(end_time)

    logging.info(f"Generating Report for: {shift_label}")
    logging.info(f"Time Window: {start_time} to {end_time}")

    # Fetch records modified recently (broad filter, refine in loop)
    # Fetching last 24h to be safe
    logging.info("Fetching recent records...")
    records = table.all(formula="NOT({AI Chat Log} = '')", max_records=2000)
    
    stats = {
        'total_processed': 0,
        'total_sent': 0,
        'total_drafts': 0,
        'draft_details': [],
        'raw_messages': [], # New: Store raw messages for bulk AI analysis
        'global_inquiries': Counter(),
        'sharm': {'total': 0, 'sent': 0, 'drafts': 0, 'inquiries': Counter()},
        'shift1': {'total': 0, 'sent': 0, 'drafts': 0, 'inquiries': Counter()},
        'shift2': {'total': 0, 'sent': 0, 'drafts': 0, 'inquiries': Counter()},
        'shift3': {'total': 0, 'sent': 0, 'drafts': 0, 'inquiries': Counter()},
        'current_shift_stats': {'total': 0, 'sent': 0, 'drafts': 0, 'inquiries': Counter()} 
    }

    logging.info(f"Analyzing {len(records)} records...")

    import re

    for rec in records:
        fields = rec['fields']
        chat_log = fields.get('AI Chat Log', '')
        
        if not chat_log: continue
        
        # EXTRACT TIMESTAMPS & FILTER
        # ... (timestamp filtering logic remains same) ...
        timestamps = re.findall(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', chat_log)
        if not timestamps: continue
        
        in_window = False
        # We need to find the LAST customer message in this window to use as "Question"
        last_customer_msg = "No message found"
        
        # Split log into lines to process messages within window
        log_lines = chat_log.split('\n')
        
        for line in log_lines:
            # Check if line has timestamp
            ts_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
            if ts_match:
                ts_str = ts_match.group(1)
                try:
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    ts = pytz.timezone('Africa/Cairo').localize(ts)
                    
                    if start_time <= ts <= end_time:
                        in_window = True
                        
                        # Extract Customer Message for "Top Questions" analysis
                        # Format: [Date] [Source - Sender]: Message
                        if " - Customer]" in line or " - User]" in line: # Adjust based on your log format
                            parts = line.split(']: ', 1)
                            if len(parts) > 1:
                                msg_content = parts[1].strip()
                                last_customer_msg = msg_content
                                
                                # Add to raw messages for AI analysis later
                                if len(msg_content) > 5:
                                    stats['raw_messages'].append(msg_content)
                                    
                except:
                    continue
                
        if not in_window:
            continue

        # --- RECORD IS RELEVANT FOR THIS SHIFT ---
        
        # Determine Category
        is_sharm = is_sharm_booking(fields)
        
        # Determine Status
        status = fields.get('AI Chat Status', '')
        inquiry = fields.get('Inquiry Type', 'General')
        
        is_draft = "DRAFT" in str(status).upper() or "[PROPOSED_DRAFT]" in chat_log
        is_sent = not is_draft 
        
        # Global Stats (for this shift window)
        stats['total_processed'] += 1
        stats['global_inquiries'][inquiry] += 1
        if is_sent: stats['total_sent'] += 1
        else: stats['total_drafts'] += 1
        
        # Draft Details
        if is_draft or is_sent: # Check ALL interactions, not just current drafts
            booking_nr = fields.get('Booking Nr.', 'N/A')
            customer_email = fields.get('Customer Email', 'N/A')
            
            # Determine Exact Interaction Type
            interaction_type = analyze_interaction_type(chat_log, start_time, end_time)
            
            # Use AI to summarize the last message/context
            ai_summary = summarize_text_with_ai(last_customer_msg)
            
            # Only add to detailed list if it's significant (Draft, Edited, or Human Reply)
            # Skip pure AI Auto replies to keep list focused (unless you want them)
            if interaction_type in ['DRAFT_PENDING', 'DRAFT_EDITED', 'HUMAN_REPLY', 'DRAFT_APPROVED']:
                stats['draft_details'].append({
                    'booking_nr': booking_nr,
                    'email': customer_email,
                    'inquiry': inquiry or "Unclassified",
                    'summary': ai_summary,
                    'type': interaction_type # Add Type
                })

        # Regional / Shift Stats
        # Since we are running FOR a specific shift, 'current_shift_stats' mirrors the global processed
        stats['current_shift_stats']['total'] += 1
        if is_sent: stats['current_shift_stats']['sent'] += 1
        else: stats['current_shift_stats']['drafts'] += 1
        stats['current_shift_stats']['inquiries'][inquiry] += 1

        if is_sharm:
            stats['sharm']['total'] += 1
            if is_sent: stats['sharm']['sent'] += 1
            else: stats['sharm']['drafts'] += 1
            stats['sharm']['inquiries'][inquiry] += 1

    # AI Analysis for Top Questions
    logging.info("Running AI analysis on customer messages...")
    stats['top_questions_grouped'] = analyze_top_questions_with_ai(stats['raw_messages'])
            
    # Generate HTML (Modified to focus on Current Shift)
    
    # Sort draft_details by Inquiry Type before passing to template
    if stats['draft_details']:
        stats['draft_details'].sort(key=lambda x: str(x['inquiry']))

    # Removing old function call inside this file, using imported one
    # html_report = generate_html_report(stats, now_cairo.strftime("%Y-%m-%d %H:%M"))
    html_report = generate_shift_html_report(stats, now_cairo.strftime("%Y-%m-%d"), shift_label)
    
    # Upload to Cloudinary
    setup_cloudinary()
    report_name = f"Report_{shift_label.replace(' ', '_').replace(':', '')}_{now_cairo.strftime('%Y%m%d')}.html"
    report_url = upload_html_to_cloudinary(html_report, report_name)
    
    # Send Webhook
    logging.info("Sending report to Webhook...")
    try:
        response = requests.post(
            WEBHOOK_URL, 
            json={
                "html": html_report, 
                "report_url": report_url, 
                "date": now_cairo.strftime("%Y-%m-%d"), 
                "shift": shift_label,
                "stats": str(stats)
            },
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            logging.info("Report sent successfully!")
        elif response.status_code == 204:
             logging.info("Report sent successfully (No Content)!")
        elif "Accepted" in response.text:
             logging.info("Report sent successfully (Accepted)!")
        else:
            logging.error(f"Webhook failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        logging.error(f"Failed to send webhook: {e}")

if __name__ == "__main__":
    main()
