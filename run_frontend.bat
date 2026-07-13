@echo off
cd /d "%~dp0frontend"
echo [datasentry] Starting frontend...
echo [datasentry] URL: http://localhost:3000
echo.
npm run dev > frontend.log 2>&1