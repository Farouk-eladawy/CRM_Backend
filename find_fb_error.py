import json
import re

def find_error_in_logs():
    print("Searching for the error in agent_log.txt...")
    found = False
    try:
        with open('agent_log.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Read backwards to find the most recent occurrence
            for i, line in enumerate(reversed(lines)):
                if "Failed to send Facebook message" in line and "(#10)" in line:
                    print("\n--- ERROR FOUND ---")
                    print(line.strip())
                    print("\n--- CONTEXT (Messages before the error) ---")
                    # Print 5 lines before the error to see what triggered it
                    # Since we are iterating in reverse, the lines "before" chronologically 
                    # are at indices (len(lines) - 1 - i - 5) to (len(lines) - 1 - i)
                    actual_idx = len(lines) - 1 - i
                    start_idx = max(0, actual_idx - 10)
                    for j in range(start_idx, actual_idx):
                        print(lines[j].strip())
                    found = True
                    break
    except FileNotFoundError:
        print("agent_log.txt not found.")
        
    if not found:
        print("Error not found in agent_log.txt")

if __name__ == '__main__':
    find_error_in_logs()
