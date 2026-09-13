@echo off
echo ===================================================
echo Running ZeroDayAI Backend Test Suite (.venv)
echo ===================================================

cd /d "%~dp0\..\backend"
call .venv\Scripts\activate.bat
python -m pytest tests -v
