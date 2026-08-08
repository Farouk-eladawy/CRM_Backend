with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will define get_pending_outbox_for_prompt and call it right before knowledge_context is built
# Or actually inside _build_pi_real_analysis_prompt

function_str = '''
def get_pending_outbox_for_prompt(user_key):
    import os, glob, json
    outbox_dir = os.path.join('runtime', 'pi_brain', 'users', user_key, 'bridge', 'outbox')
    if not os.path.exists(outbox_dir): return ''
    files = glob.glob(os.path.join(outbox_dir, '*.json'))
    pending = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                pending.append(f"- Action: {data.get('action_type', 'Unknown')} | Payload: {json.dumps(data.get('action_payload', {}), ensure_ascii=False)}")
        except: pass
    if not pending: return ''
    return '=== PENDING REQUESTS (WAITING FOR BACKGROUND EXECUTION) ===\\n' + '\\n'.join(pending) + '\\n\\nIMPORTANT: You must inform the user in your reply that these requests are still pending and being processed.\\n\\n'
'''

# Find a good place to inject this function. At the top of _build_pi_real_analysis_prompt or global scope.
# Let's put it right before def _build_pi_real_analysis_prompt:

if "def get_pending_outbox_for_prompt" not in content:
    content = content.replace("def _build_pi_real_analysis_prompt", function_str + "\ndef _build_pi_real_analysis_prompt")

# Then inside _build_pi_real_analysis_prompt, call it:
old_block = '''                  user_key = f"u_{str(actor.get('username') or 'internal').lower()}"
                      full_context = ke.get_full_context_for_pi(user_key=user_key, action_intent=prompt_payload.get("intent"), user_request=user_request)'''

new_block = '''                  user_key = f"u_{str(actor.get('username') or 'internal').lower()}"
                      full_context = ke.get_full_context_for_pi(user_key=user_key, action_intent=prompt_payload.get("intent"), user_request=user_request)
                      pending_outbox_str = get_pending_outbox_for_prompt(user_key)'''

if old_block in content:
    content = content.replace(old_block, new_block)
    
# And inject pending_outbox_str into knowledge_context
old_context = '''                          f"{full_context.get('dynamic_knowledge', '')}\n\n"
                          "=== DATABASE SCHEMA (AIRTABLE) ===\n"'''

new_context = '''                          f"{full_context.get('dynamic_knowledge', '')}\n\n"
                          f"{pending_outbox_str}"
                          "=== DATABASE SCHEMA (AIRTABLE) ===\n"'''

if old_context in content:
    content = content.replace(old_context, new_context)

with open('ai_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESS updated ai_agent.py for pending requests")
