@echo off
echo ========================================================
echo FTS Travels CRM - Environment Setup
echo ========================================================

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.10+ and ensure "Add Python to PATH" is checked during installation.
    pause
    exit /b 1
)

echo [1/3] Upgrading pip...
python -m pip install --upgrade pip

echo [2/3] Installing required libraries from requirements.txt...
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo [ERROR] requirements.txt not found!
    echo Please ensure the file is in the same directory as this script.
    pause
    exit /b 1
)

echo [3/3] Checking NSSM (Non-Sucking Service Manager) presence...
if not exist "nssm.exe" (
    echo [WARNING] nssm.exe not found in the current directory.
    echo You will need nssm.exe to install the FTS Teacher service.
) else (
    echo [OK] NSSM found.
)

echo ========================================================
echo [SUCCESS] Environment setup complete!
echo You can now run "install_teacher_service.bat" to setup the backend.
echo ========================================================
pause
