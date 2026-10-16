@echo off
rem Prod mode: build frontend once, then FastAPI serves dist on single port 8001
setlocal

set "PROJECT=D:\11.project\iwen-codex\codex-list\training-tracker-docker"
set "BACKEND=%PROJECT%\web\backend"
set "FRONTEND=%PROJECT%\web\frontend"

echo [1/3] Building frontend (npm run build) ...
cd /d "%FRONTEND%"
call npm run build
if errorlevel 1 (
    echo BUILD FAILED - aborting.
    pause
    exit /b 1
)

echo [2/3] Starting FastAPI (serving dist) on http://127.0.0.1:8001 ...
start "training-backend-prod" cmd /k "cd /d %BACKEND% && python -m uvicorn app.main:app --host 127.0.0.1 --port 8001"

echo [3/3] Opening browser ...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:8001

echo.
echo To rebuild after frontend changes: run this script again.
pause
