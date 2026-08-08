import subprocess
p = subprocess.Popen(
    ["python", "-c", "import sys; sys.stdout.buffer.write(b'\\x81\\n')"], 
    stdout=subprocess.PIPE, 
    stderr=subprocess.PIPE, 
    text=True, 
    encoding="utf-8", 
    errors="replace"
)
print(p.communicate())
