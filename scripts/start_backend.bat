@echo off
echo ===================================================
echo Starting ZeroDayAI FastAPI Backend (.venv)
echo ===================================================

cd /d "%~dp0\.."

if not exist "backend\.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment backend\.venv not found!
    echo Please run scripts\setup_env.bat first.
    pause
    exit /b 1
)

call backend\.venv\Scripts\activate.bat
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
