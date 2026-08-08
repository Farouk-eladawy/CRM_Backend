with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The error is that I replaced the block, but left the old lse: block from line 299 downwards.
# Let's find the end of this duplicate block which should be around line 352
end_idx = 0
for i in range(298, len(lines)):
    if 'elif action_type == "update_records":' in lines[i] or 'elif action_type == "create_records":' in lines[i]:
        end_idx = i
        break

if end_idx > 0:
    del lines[298:end_idx]
    with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("SUCCESS removed duplicate block")
else:
    print("FAILED to find end of block")
