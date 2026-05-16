@echo off
REM =========================================================
REM Nova Ultimate 2026 Phase 6
REM Single-Click Launch for Endgame Portable Build
REM =========================================================

SET "BUILD_DIR=C:\Users\Owner\nova_phase6_portable\dist"
SET "EXE_NAME=app.exe"  REM Replace if PyInstaller executable has a different name

IF NOT EXIST "%BUILD_DIR%\%EXE_NAME%" (
    ECHO [ERROR] Nova executable not found! Run PHASE6_ENDGAME_PORTABLE.ps1 first.
    PAUSE
    EXIT /B 1
)

ECHO Launching Nova Ultimate 2026 Phase 6...
START "" "%BUILD_DIR%\%EXE_NAME%"
EXIT /B 0