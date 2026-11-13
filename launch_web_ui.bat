@echo off
REM ═══════════════════════════════════════════════════════════════
REM  SITE Assets Monitor — HITL Web UI Launcher
REM  Usage:  launch_web_ui.bat [path\to\video.mp4]
REM  Then open:  http://localhost:8000
REM ═══════════════════════════════════════════════════════════════

cd /d "%~dp0"

if not "%~1"=="" (
    echo [INFO] Setting video: %~1
    set HITL_VIDEO_PATH=%~1
)

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   SITE Assets Monitor  —  HITL Web UI               ║
echo  ║   Open Chrome/Edge at:  http://localhost:8000        ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

python -m uvicorn web_ui.server:app --host 0.0.0.0 --port 8000 --app-dir .
