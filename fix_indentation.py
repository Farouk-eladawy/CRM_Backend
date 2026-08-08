with open('ai_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We know the block starts around 14123
# We need to add 12 spaces to lines from 14123 to 14138.
for i in range(14122, 14139):
    if not lines[i].startswith('            '):
        lines[i] = '            ' + lines[i]

with open('ai_agent.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("SUCCESS fixed indentation")
