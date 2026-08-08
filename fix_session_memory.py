with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find _clear_internal_session and change it so that it DOES NOT clear recent_turns, or maybe we just don't clear it.
# The user complains: "Started a new session but the problem is he doesn't understand. I want a root solution for knowing the conversation context even if you save it in a file per user to speed up reviewing the conversation or current session"
# If the user says "جلسة جديدة" (new session), _clear_internal_session is called.
# The user wants PI to *still* understand the context of the conversation even across "sessions", or to persist it.

# Let's change _clear_internal_session so that it DOES NOT clear ecent_turns, OR we create a persistent_turns array.
# Actually, the user specifically says: "حتي لو هتسجلها في ملف لكل مستخدم" (even if you save it in a file for each user).
# Let's create a persistent file logging for each internal user.

import re

# We will modify _append_turn to also write to a file: untime/pi_brain/users/{actor_name}/conversation_log.txt
# But i_agent.py might already have something like this.
# Let's just modify _append_turn to append to a file.

