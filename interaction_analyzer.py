from datetime import datetime
import pytz
import re

def analyze_interaction_type(chat_log, start_time, end_time):
    """
    Analyzes the chat log to determine the interaction type within the shift window.
    Returns: (Interaction Type Code, Description)
    Types: 'AI_AUTO', 'DRAFT_PENDING', 'DRAFT_APPROVED', 'DRAFT_EDITED', 'HUMAN_REPLY'
    """
    if not chat_log:
        return 'UNKNOWN', 'No Log'
        
    lines = chat_log.split('\n')
    
    last_draft = None
    last_draft_time = None
    
    interaction_type = 'UNKNOWN'
    
    # We need to scan chronologically
    for line in lines:
        # Extract timestamp
        ts_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
        if not ts_match: continue
        
        try:
            ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S")
            ts = pytz.timezone('Africa/Cairo').localize(ts)
        except:
            continue
            
        if not (start_time <= ts <= end_time):
            continue
            
        # Analyze Content
        content = line.lower()
        
        if "[proposed_draft]" in content:
            last_draft = line.split("]:", 1)[1].strip() if "]:" in line else ""
            last_draft_time = ts
            interaction_type = 'DRAFT_PENDING' # Tentative
            
        elif " - user]" in content or " - support]" in content or " - agent]" in content:
            # This is a message sent by a human/system to the customer
            sent_msg = line.split("]:", 1)[1].strip() if "]:" in line else ""
            
            if last_draft and last_draft_time:
                # Check similarity
                # Simple check: if > 80% similar, it's approved. Else edited.
                # For speed, we just check if draft is IN the sent message or vice versa
                if last_draft in sent_msg or sent_msg in last_draft:
                    interaction_type = 'DRAFT_APPROVED'
                else:
                    interaction_type = 'DRAFT_EDITED'
                
                # Reset draft after matching
                last_draft = None 
                last_draft_time = None
            else:
                # No draft preceded this message -> Human Reply
                interaction_type = 'HUMAN_REPLY'
                
        elif "[ai_auto_reply]" in content or "[sent_by_ai]" in content:
             interaction_type = 'AI_AUTO'
             
    return interaction_type
