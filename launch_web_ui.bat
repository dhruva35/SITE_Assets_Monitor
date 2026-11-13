@echo off
REM ============================================================
REM  SITE Assets Monitor - HITL Web UI Launcher
REM  Usage:  launch_web_ui.bat [path\to\video.mp4]
REM ============================================================

cd /d "%~dp0"
set "PYTHONPATH=%~dp0"

REM Pick virtualenv python if present, else fallback to system python
if exist "%~dp0venv\Scripts\python.exe" (
    set "PY_BIN=%~dp0venv\Scripts\python.exe"
) else (
    set "PY_BIN=python"
)

REM Set video path if passed as argument
if not "%~1"=="" (
    echo [INFO] Video specified: %~1
    set "HITL_VIDEO_PATH=%~1"
)

echo.
echo ======================================================
echo    SITE Assets Monitor - HITL Web UI
echo    Starting server and opening http://localhost:8000
echo ======================================================
echo.

REM Open browser in 2 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

REM Run server
"%PY_BIN%" -m uvicorn web_ui.server:app --host 0.0.0.0 --port 8000 --app-dir "%~dp0."

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server terminated with error code %ERRORLEVEL%.
    pause
)
