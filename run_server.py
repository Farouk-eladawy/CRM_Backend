import subprocess
import sys
import os
import time

script_dir = os.path.join(
    'C:\\', 'Users', 'Aloosh2020', 'Downloads',
    "New Project's", 'AIAgentProject', 'OpenClaw_Version'
)
os.chdir(script_dir)
print(f"Working dir: {os.getcwd()}")

# Activate venv and start server
venv_python = os.path.join(script_dir, '.venv', 'Scripts', 'python.exe')
if os.path.exists(venv_python):
    python_exe = venv_python
else:
    python_exe = sys.executable

print(f"Using Python: {python_exe}")

proc = subprocess.Popen(
    [python_exe, 'ai_agent.py'],
    cwd=script_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
print(f"Started PID: {proc.pid}")

time.sleep(6)
poll = proc.poll()
if poll is None:
    print("SUCCESS: Server is running!")
    # Test the new routes
    import urllib.request
    try:
        req = urllib.request.Request('http://127.0.0.1:5001/api/git/settings')
        resp = urllib.request.urlopen(req, timeout=5)
        print(f"Test OK: GET /api/git/settings -> {resp.status}")
    except Exception as e:
        print(f"Test result: {e}")
else:
    out, err = proc.communicate(timeout=3)
    print(f"FAILED: Exit code {poll}")
    if err:
        print(f"STDERR:\n{err[:2000]}")
