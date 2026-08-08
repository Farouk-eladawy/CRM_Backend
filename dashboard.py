import time
import os

LOG_FILE = "system.log"

def follow(thefile):
    """Generator function that yields new lines in a file"""
    # Seek to the end of the file
    thefile.seek(0, os.SEEK_END)
    
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.5) # Sleep briefly
            continue
        yield line

def main():
    print("===================================================")
    print("       FTS Travels - Live Dashboard Monitoring     ")
    print("===================================================")
    print("Waiting for events...\n")

    # Create file if not exists
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write("--- Log Started ---\n")

    with open(LOG_FILE, 'r', encoding='utf-8') as logfile:
        # Show last 10 lines first
        lines = logfile.readlines()
        for line in lines[-10:]:
            print(line.strip())
            
        # Follow new lines
        for line in follow(logfile):
            line = line.strip()
            if "[Bridge]" in line:
                print(f"🔵 {line}") # Blue/Neutral for Bridge
            elif "[OpenClaw Core]" in line:
                if "Draft Response" in line:
                    print(f"🟡 {line}") # Yellow for Drafts
                elif "Intent" in line:
                    print(f"🟣 {line}") # Purple for Intents
                else:
                    print(f"🟢 {line}") # Green for Core
            else:
                print(line)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
