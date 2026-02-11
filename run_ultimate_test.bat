@echo off
REM Ultimate Testing & Maintenance Script Runner
REM This batch file runs the ultimate testing and maintenance script

echo ========================================
echo Ultimate Testing & Maintenance Script
echo ========================================
echo.

REM Check if Python venv is available
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found at .venv
    echo Please run: python -m venv .venv && .venv\Scripts\activate && pip install -e .
    pause
    exit /b 1
)

REM Run the ultimate testing and maintenance script
echo Running ultimate testing and maintenance script...
echo This may take several minutes...
echo.

".venv\Scripts\python.exe" ultimate_test_maintenance.py %*

echo.
echo ========================================
echo Script execution completed!
echo Check the logs/ directory for detailed results:
echo - feature_test_results.txt (test results)
echo - cleanup_log.txt (cleanup actions)
echo - summary_report.txt (comprehensive report)
echo ========================================
echo.

pause