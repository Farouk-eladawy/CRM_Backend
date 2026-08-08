"""Simple script to start ai_agent.py server in background"""
import subprocess
import sys
import os
import time

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

print(f"Starting ai_agent.py from: {script_dir}")
print(f"Python: {sys.executable}")

# Start the server process
proc = subprocess.Popen(
    [sys.executable, '-u', 'ai_agent.py'],
    cwd=script_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
)

# Wait a moment for it to start
time.sleep(4)

# Check status
poll = proc.poll()
if poll is None:
    print(f"SUCCESS: Server running with PID: {proc.pid}")
else:
    stdout, stderr = proc.communicate(timeout=3)
    print(f"FAILED: Server exited with code: {poll}")
    if stdout:
        out_text = stdout.decode('utf-8', errors='replace')
        print(f"STDOUT:\n{out_text[:1000]}")
    if stderr:
        err_text = stderr.decode('utf-8', errors='replace')
        print(f"STDERR:\n{err_text[:1000]}")
