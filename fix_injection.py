import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I will find the block that does silent data injection and stop it from blindly grabbing data when the user asks ambiguous questions.
# The issue is that the code manually injects data based on keywords: report_keywords = ["تقرير", "تقارير", "حجوزات", "حجز", "bookings", "report", "pickup", "بيك اب", "محتاج مراجعة", "ملغي"]
# And then it checks: if any(term in txt_lower for term in ["اليوم", "النهارده", "النهاردة", "today"]): v_name = "Operation Today"
# And then it injects: "[SYSTEM DATA INJECTION: The following is REAL data from Airtable view 'Operation Today'. Use this data to answer the user's request. Do NOT hallucinate data...]"
# Since it injects the data directly into the user_request, PI sees the data and answers immediately without asking the clarifying questions we programmed it to ask.
# We need to disable this manual injection or make it smarter. Since we already gave PI the ability to query Airtable natively via query_records schema, this silent injection is actually overriding PI's brain!
# Let's remove this hardcoded injection completely and let PI handle it via the schemas and intelligence we just built!

old_block_start = "# --- SYSTEM DATA INJECTION FOR DYNAMIC REPORTS ---"
old_block_end = "injected_data = f\"\\n\\n[SYSTEM DATA INJECTION: Failed to fetch real data from Airtable. Error: {e}]\""

idx1 = content.find(old_block_start)
idx2 = content.find(old_block_end)

if idx1 != -1 and idx2 != -1:
    idx2 += len(old_block_end)
    
    # We replace it with nothing, but we still need injected_data = "" because it's used later.
    new_block = '''# --- REMOVED SILENT DATA INJECTION ---
                      # We now rely on PI's native schemas and orchestration rules to fetch data smartly.
                      injected_data = ""'''
    
    content = content[:idx1] + new_block + content[idx2:]
    with open('ai_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS removed silent injection")
else:
    print("FAILED to find block")
