@echo off
setlocal
cd /d "%~dp0"

if not exist build.local.json (
    echo ERROR: build.local.json is missing.
    echo.
    echo Copy:
    echo   build.local.example.json
    echo to:
    echo   build.local.json
    echo.
    echo Then set "game_version" to the exact current folder under:
    echo   World of Tanks\mods\
    echo.
    pause
    exit /b 1
)

call build.bat --install
exit /b %errorlevel%
