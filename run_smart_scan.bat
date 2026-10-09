@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" smart_scan.py %*
) else (
    python smart_scan.py %*
)
if errorlevel 1 pause
