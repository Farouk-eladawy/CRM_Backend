import re

def parse_logs():
    with open('agent_log.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if "03:47:07" in line and "Failed to send Facebook message" in line:
                print("--- Found Error Line ---")
                print(line.strip())
                print("--- Context ---")
                start = max(0, i - 15)
                end = min(len(lines), i + 5)
                for j in range(start, end):
                    print(lines[j].strip())
                break

if __name__ == '__main__':
    parse_logs()