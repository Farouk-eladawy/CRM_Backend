with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ah! rom datetime import datetime is at the top of the file!
# But in our code we used datetime.datetime.now(). Since it's imported as rom datetime import datetime, we should just use datetime.now().
# Or we can change rom datetime import datetime to import datetime. But other parts of the file might rely on rom datetime import datetime.
# Let's change our code to use datetime.now() and datetime.timedelta. Wait, 	imedelta is not imported!
# Let's just add import datetime as dt at the top and use dt.datetime.now().

if "import datetime as dt" not in content:
    content = "import datetime as dt\n" + content
    
content = content.replace("datetime.datetime.now()", "dt.datetime.now()")
content = content.replace("datetime.timedelta", "dt.timedelta")

with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESS fixed datetime module issue completely")
