@echo off
REM =========================================================
REM Nova Ultimate 2026 Phase 6
REM Single-click portable launcher
REM =========================================================

REM Set paths
SET "BUILD_DIR=C:\Users\Owner\nova_build_portable\dist"
SET "EXE_NAME=app.exe"  REM Replace with actual PyInstaller executable name if different

REM Check if executable exists
IF NOT EXIST "%BUILD_DIR%\%EXE_NAME%" (
    ECHO [ERROR] Nova executable not found! Run BUILD_PORTABLE_QUICK.ps1 first.
    PAUSE
    EXIT /B 1
)

REM Launch Nova
ECHO Launching Nova Ultimate 2026 Phase 6...
START "" "%BUILD_DIR%\%EXE_NAME%"
EXIT /B 0
