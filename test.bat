@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if not errorlevel 1 (
    py -3 tests\test_toggle_ptt.py
    exit /b %errorlevel%
)

where python >nul 2>&1
if not errorlevel 1 (
    python tests\test_toggle_ptt.py
    exit /b %errorlevel%
)

echo ERROR: Python 3 was not found for the local mock tests.
pause
exit /b 1
