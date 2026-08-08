import subprocess, sys, os, time

script_dir = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version"
os.chdir(script_dir)

print(f"Starting from: {script_dir}")
print(f"Python: {sys.executable}")

proc = subprocess.Popen(
    [sys.executable, '-u', 'ai_agent.py'],
    cwd=script_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

time.sleep(8)
poll = proc.poll()

if poll is None:
    print(f"SUCCESS: PID={proc.pid}")
    # Keep it running, just check
    stdout, stderr = proc.communicate(timeout=1)
else:
    stdout, stderr = proc.communicate(timeout=3)
    print(f"EXIT CODE: {poll}")
    if stdout:
        print(f"STDOUT:\n{stdout[:3000]}")
    if stderr:
        print(f"STDERR:\n{stderr[:3000]}")
