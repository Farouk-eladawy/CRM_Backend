import os
import sys

# Change cwd to load config.json correctly if needed
sys.path.append(r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version")
os.chdir(r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version")

from ai_agent import AIAgent

agent = AIAgent()

try:
    rec1 = agent.table.get("recnMhYp0emqZ27Rl")
    print("Found in Main Table:")
    print(rec1)
except Exception as e:
    print("Not in main table:", e)

try:
    if agent.religious_leads_table:
        rec2 = agent.religious_leads_table.get("recnMhYp0emqZ27Rl")
        print("\nFound in Religious Leads Table:")
        print(rec2)
except Exception as e:
    print("Not in religious table:", e)

