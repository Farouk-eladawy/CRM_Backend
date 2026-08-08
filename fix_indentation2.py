with open('ai_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(14122, 14139):
    line = lines[i].lstrip()
    if not line:
        continue
    if "def get_pending_outbox_for_prompt" in line:
        lines[i] = "            " + line
    elif "import os, glob, json" in line:
        lines[i] = "                " + line
    elif "outbox_dir =" in line:
        lines[i] = "                " + line
    elif "if not os.path.exists" in line:
        lines[i] = "                " + line
    elif "files = glob.glob" in line:
        lines[i] = "                " + line
    elif "pending = []" in line:
        lines[i] = "                " + line
    elif "for f in files:" in line:
        lines[i] = "                " + line
    elif "try:" in line:
        lines[i] = "                    " + line
    elif "with open(" in line:
        lines[i] = "                        " + line
    elif "data = json.load(" in line:
        lines[i] = "                            " + line
    elif "pending.append(" in line:
        lines[i] = "                            " + line
    elif "except:" in line:
        lines[i] = "                    " + line
    elif "if not pending:" in line:
        lines[i] = "                " + line
    elif "return '=== PENDING" in line:
        lines[i] = "                " + line
    elif "def _build_pi_real_analysis_prompt" in line:
        lines[i] = "            " + line

with open('ai_agent.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("SUCCESS fixed indentation 2")
