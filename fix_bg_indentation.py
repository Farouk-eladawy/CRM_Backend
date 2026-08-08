with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(299, 345):
    line = lines[i]
    if line.strip():  # If not empty
        lines[i] = "            " + line

with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS fixed background engine indentation")
