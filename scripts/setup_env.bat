@echo off
echo ===================================================
echo Setting up ZeroDayAI Backend Python Virtual Environment
echo ===================================================

cd /d "%~dp0\..\backend"

if not exist ".venv" (
    echo Creating virtual environment .venv...
    python -m venv .venv
)

echo Activating .venv and upgrading pip...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo Environment setup complete!
