@echo off
cd /d "%~dp0backend"
echo [datasentry] Starting backend...
echo [datasentry] Log: backend\backend.log
echo [datasentry] URL: http://localhost:8000
echo [datasentry] Docs: http://localhost:8000/docs
echo.
call .venv\Scripts\activate.bat
uvicorn app.main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1