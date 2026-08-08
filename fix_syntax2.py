with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# It looks like there's still a duplicate block starting at 299: lse:
# The correct next elif is lif action_type in ["update_record", "update_airtable"]:
# Let's find where that next elif is, and delete everything between 298 and that next elif.

start_del = 298 # index 298 is line 299
end_del = -1

for i in range(298, len(lines)):
    if 'elif action_type in ["update_record", "update_airtable"]:' in lines[i]:
        end_del = i
        break

if end_del != -1:
    del lines[start_del:end_del]
    with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"SUCCESS deleted from {start_del} to {end_del}")
else:
    print("FAILED could not find the next elif")
