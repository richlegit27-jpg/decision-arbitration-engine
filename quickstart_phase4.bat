@echo off
REM -----------------------------
REM Phase 4 Nova Quickstart Script
REM -----------------------------

REM 1. Navigate to Nova folder
cd /d C:\Users\Owner\nova

REM 2. Ensure demo media exists
if not exist "static\demo\image1.png" echo WARNING: Demo image missing
if not exist "static\demo\sample.pdf" echo WARNING: Demo PDF missing
if not exist "static\demo\video.mp4" echo WARNING: Demo video missing

REM 3. Start Flask server
echo Starting Flask Phase 4 server on http://127.0.0.1:8743 ...
start "" python app.py

REM 4. Wait a few seconds then open default browser
timeout /t 5 >nul
start "" http://127.0.0.1:8743/

echo Nova Phase 4 quickstart complete!
pause