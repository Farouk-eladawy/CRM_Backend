import re

with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to add 'import datetime' at the top of the file, or right before we use it, but since it's failing locally,
# we should make sure 'import datetime' is at the top of background_task_engine.py

if "import datetime" not in content:
    content = "import datetime\n" + content
    with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS added import datetime at the top")
else:
    print("datetime already imported? Let me check where it is failing.")
    
# The error says "cannot access local variable 'datetime' where it is not associated with a value". 
# This happens in Python if we have import datetime inside a loop or function block, but then we use it in a way that Python thinks it's a local variable before it's assigned.
# Let's fix this by putting import datetime at the very top of the file.

# Let's remove the local import datetime if it exists.
content = content.replace("                                    import datetime\n", "")
if "import datetime" not in content:
    content = "import datetime\n" + content

with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESS fixed datetime local variable issue")
