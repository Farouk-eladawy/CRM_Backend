import json
import re

def find_error_551_in_logs():
    print("Searching for error 551 in agent_log.txt...")
    found = False
    try:
        with open('agent_log.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(reversed(lines)):
                if "Failed to send Facebook message" in line and "(#551)" in line:
                    print("\n--- ERROR FOUND ---")
                    print(line.strip())
                    print("\n--- CONTEXT (Messages before the error) ---")
                    actual_idx = len(lines) - 1 - i
                    start_idx = max(0, actual_idx - 10)
                    for j in range(start_idx, actual_idx):
                        print(lines[j].strip())
                    found = True
                    break
    except FileNotFoundError:
        print("agent_log.txt not found.")

if __name__ == '__main__':
    find_error_551_in_logs()
