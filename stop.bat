@echo off
echo Stopping Intel-AI App...
REM Kill API on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do taskkill /PID %%a /F >nul 2>&1
REM Kill dashboard on port 3000 (Node.js)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000') do taskkill /PID %%a /F >nul 2>&1
REM Kill browser processes (generic approach)
taskkill /IM "chrome.exe" /F >nul 2>&1
taskkill /IM "firefox.exe" /F >nul 2>&1
taskkill /IM "msedge.exe" /F >nul 2>&1
taskkill /IM "DuckDuckGo.exe" /F >nul 2>&1
taskkill /IM "DuckDuckGo.DesktopBrowser.exe" /F >nul 2>&1
REM Also try to kill any browser processes that might be running localhost:3000
for /f "tokens=2" %%i in ('tasklist /FI "WINDOWTITLE eq http://localhost:3000*" /FO LIST 2^>nul ^| find "PID:"') do taskkill /PID %%i /F >nul 2>&1
echo App stopped.
pause