from playwright.sync_api import sync_playwright
import os

FILE_PATH = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\Supply Partner _ Products.html"

def test_selectors():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        
        url = f"file:///{FILE_PATH.replace(os.sep, '/')}"
        print(f"Opening: {url}")
        page.goto(url)
        
        print("\n--- Testing Selectors ---")
        
        # 1. Product ID Debug
        print("\n--- Product ID Debug ---")
        try:
            pid_el = page.get_by_text("Product Id:", exact=False).first
            print(f"PID Element HTML: {pid_el.evaluate('el => el.outerHTML')}")
            print(f"PID Parent HTML: {pid_el.locator('..').evaluate('el => el.outerHTML')}")
        except:
            print("PID element not found")

        # 2. Descriptions Debug
        print("\n--- Descriptions Debug ---")
        try:
            desc_label = page.get_by_text("Short description", exact=True).first
            print(f"Label HTML: {desc_label.evaluate('el => el.outerHTML')}")
            print(f"Parent HTML: {desc_label.locator('..').evaluate('el => el.outerHTML')}")
            print(f"Sibling HTML: {desc_label.locator('xpath=following-sibling::*').first.evaluate('el => el.outerHTML')}")
        except:
            print("Short description label not found")
            
        # 3. Highlights Debug
        print("\n--- Highlights Debug ---")
        try:
            hl_label = page.get_by_text("Highlights", exact=True).first
            print(f"HL Label HTML: {hl_label.evaluate('el => el.outerHTML')}")
            print(f"HL Parent HTML: {hl_label.locator('..').evaluate('el => el.outerHTML')}")
        except:
            print("Highlights label not found")

        # 4. Full Desc & Inclusions Debug
        print("\n--- Full Desc & Inclusions Debug ---")
        try:
            fd = page.locator("xpath=//span[contains(text(), 'Full description')]/following-sibling::*")
            print(f"Full Desc Sibling HTML: {fd.first.evaluate('el => el.outerHTML')[:200]}...")
        except: print("FD not found")

        try:
            inc = page.locator("xpath=//span[contains(text(), 'Inclusions')]/following-sibling::*")
            print(f"Inclusions Sibling HTML: {inc.first.evaluate('el => el.outerHTML')[:200]}...")
        except: print("Inc not found")


        browser.close()

if __name__ == "__main__":
    test_selectors()
