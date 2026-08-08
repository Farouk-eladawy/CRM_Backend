import os

file_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\frontend_dashboard\new_frontend_dashboard\src\App.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("if (p === '/automation') return 'automation';", "if (p === '/automation') return 'automation';\n      if (p === '/sales-performance') return 'sales_performance';")
content = content.replace("if (t === 'automation') return '/automation';", "if (t === 'automation') return '/automation';\n    if (t === 'sales_performance') return '/sales-performance';")

# Also need to add the PerformanceView component import
import_stmt = "import AutomationView from './views/AutomationView';"
new_import = "import AutomationView from './views/AutomationView';\nimport PerformanceView from './views/PerformanceView';"
if new_import not in content:
    content = content.replace(import_stmt, new_import)

# And add the menu item to the sidebar
# Let's find where menu items are defined. Usually there's a list or it's hardcoded.
# We'll do it step by step.

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
