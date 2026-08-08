@echo off
if exist "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" bulletproof.py > cmd_out.txt 2>&1
) else (
    if exist ".venv\Scripts\python.exe" (
        ".venv\Scripts\python.exe" bulletproof.py > cmd_out.txt 2>&1
    ) else (
        echo Python not found > cmd_out.txt
    )
)
