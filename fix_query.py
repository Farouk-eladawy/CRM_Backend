import re

with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's fix the logic where it blindly queries 'List' or 'Trips' instead of letting PI specify the table.
# Actually, the user wants us to fix the fact that PI gave a detailed response for bookings, but the logic in background_task_engine.py only fetches raw Airtable and groups them.
# Wait, the user showed: 
# "مرحباً! إليك تفاصيل جميع الحجوزات التي تم إنشاؤها اليوم (2026-07-12) — إجمالي 46 حجزاً: "
# "📍 حجوزات Tiqets (9 حجوزات - جميعها Active):"
# This means PI used internal data (from full_context) instead of background_task_engine, or background_task_engine did it.
# Let's check ai_agent.py again.
