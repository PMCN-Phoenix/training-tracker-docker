@echo off
rem Dev mode: FastAPI backend (8001) + Vite dev server (5174)
rem Usage: double-click, or run from anywhere (paths are absolute)
setlocal

set "PROJECT=D:\11.project\iwen-codex\codex-list\training-tracker-docker"
set "BACKEND=%PROJECT%\web\backend"
set "FRONTEND=%PROJECT%\web\frontend"

echo [1/3] Starting FastAPI backend on http://127.0.0.1:8001 ...
start "training-backend" cmd /k "cd /d %BACKEND% && python -m uvicorn app.main:app --host 127.0.0.1 --port 8001"

echo [2/3] Starting Vite dev server on http://127.0.0.1:5174 ...
start "training-frontend" cmd /k "cd /d %FRONTEND% && npm run dev"

echo [3/3] Opening browser ...
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5174

echo.
echo Backend API docs: http://127.0.0.1:8001/docs
echo Close the two popped-up windows to stop.
pause
