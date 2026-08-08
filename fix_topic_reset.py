with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will modify _reset_internal_topic_state to not clear ecent_turns.

old_block = '''              def _reset_internal_topic_state(reason="new_topic"):
                  session_state["pending_action"] = {}
                  session_state["workflow_state"] = {}
                  session_state["pi_case_state"] = {}
                  session_state["last_case_context"] = {}
                  session_state["recent_turns"] = []
                  session_state["topic_reset_meta"] = {'''

new_block = '''              def _reset_internal_topic_state(reason="new_topic"):
                  session_state["pending_action"] = {}
                  session_state["workflow_state"] = {}
                  session_state["pi_case_state"] = {}
                  session_state["last_case_context"] = {}
                  # IMPORTANT: Do not clear recent_turns so PI keeps context even across sessions
                  # session_state["recent_turns"] = []
                  session_state["topic_reset_meta"] = {'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('ai_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS fixed _reset_internal_topic_state')
else:
    print('FAILED to find _reset_internal_topic_state block')
