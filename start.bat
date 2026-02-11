@echo off
echo Starting Intel-AI App...
set PYTHONIOENCODING=utf-8
powershell -Command "$env:VS_DB_MODE = 'sqlite'; $env:PYTHONIOENCODING = 'utf-8'; Start-Process -NoNewWindow -FilePath '.\.venv\Scripts\python.exe' -ArgumentList '-m uvicorn vanguard_signal.api.app:app --reload --port 8000'"
cd dashboard
start cmd /c ""C:\Program Files\nodejs\npm.cmd" run dev"
cd ..
echo App started. API on port 8000, Dashboard on port 3000.
echo Opening default browser...
start http://localhost:3000
pause