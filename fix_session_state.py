with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# The user is complaining that PI loses context across "new sessions".
# This is because the context injected in the prompt uses session_state.get("recent_turns", [])[-16:].
# If the user says "new session" or the system clears it, ecent_turns is emptied, and the bot literally has no memory of what was just said before that.
# Also, the system needs to persist the internal conversation lines to the database or a persistent file per user, so that even if the server restarts or a new session is started, it can recall the last few lines for context.

# Let's look for session_state management.
