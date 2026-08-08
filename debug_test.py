import os
import sys

print("Starting debug script...")
try:
    import playwright
    print("Playwright imported successfully.")
    from playwright.sync_api import sync_playwright
    print("sync_playwright imported.")
except ImportError as e:
    print(f"Error importing playwright: {e}")

try:
    import playwright_stealth
    print("playwright_stealth imported.")
except ImportError as e:
    print(f"Error importing playwright_stealth: {e}")

INPUT_FILE = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Viator links_test.txt"
if os.path.exists(INPUT_FILE):
    print(f"Input file exists: {INPUT_FILE}")
    with open(INPUT_FILE, 'r') as f:
        print(f"First line: {f.readline().strip()}")
else:
    print(f"Input file NOT found: {INPUT_FILE}")
