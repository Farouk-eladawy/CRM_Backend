with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# The duplicate block starts exactly at line 353 (else:) and goes until line 411.
# I will delete lines 352 to 411 (indices 352 to 411)
del lines[352:411]

with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS deleted lines")
