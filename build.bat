@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  Toggle Platoon PTT - Build
echo ============================================
echo.

if defined PYTHON27 (
    if exist "%PYTHON27%" (
        "%PYTHON27%" build.py %*
        exit /b %errorlevel%
    )
)

where py >nul 2>&1
if not errorlevel 1 (
    py -2.7 -c "import sys; assert sys.version_info[:2] == (2,7)" >nul 2>&1
    if not errorlevel 1 (
        py -2.7 build.py %*
        exit /b %errorlevel%
    )
)

if exist "C:\Python27\python.exe" (
    "C:\Python27\python.exe" build.py %*
    exit /b %errorlevel%
)

where python2.7 >nul 2>&1
if not errorlevel 1 (
    python2.7 build.py %*
    exit /b %errorlevel%
)

echo ERROR: Python 2.7.18 was not found.
echo.
echo Install Python 2.7.18, or set:
echo   set PYTHON27=C:\Python27\python.exe
echo.
pause
exit /b 1
