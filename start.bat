@echo off
echo Starting YouTube Downloader Server...
echo.

REM Check if venv exists
if not exist ".venv" (
    echo Virtual environment not found. Creating one...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt -q

REM Load .env file if it exists
if exist ".env" (
    echo Loading environment variables from .env...
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        set "%%a=%%b"
    )
)

REM Start server
echo.
echo Server starting at http://127.0.0.1:8000
echo Press CTRL+C to stop
echo.
uvicorn main:app --reload
