@echo off
REM Production Deployment Verification Script for Windows
REM Run this before deploying to catch common issues

echo ==================================
echo Pre-Deployment Checklist
echo ==================================
echo.

set PASSED=0
set FAILED=0

REM 1. Check Python version
echo Checking Python version...
python --version | findstr /C:"Python 3" >nul
if %errorlevel% equ 0 (
    echo [OK] Python 3.x installed
    set /a PASSED+=1
) else (
    echo [FAIL] Python 3.x NOT found
    set /a FAILED+=1
)

REM 2. Check if virtual environment exists
echo Checking virtual environment...
if exist ".venv\" (
    echo [OK] Virtual environment found
    set /a PASSED+=1
) else if exist "venv\" (
    echo [OK] Virtual environment found
    set /a PASSED+=1
) else (
    echo [WARN] Virtual environment not found
)

REM 3. Check requirements.txt
echo Checking requirements.txt...
if exist "requirements.txt" (
    echo [OK] requirements.txt exists
    set /a PASSED+=1
) else (
    echo [FAIL] requirements.txt NOT found
    set /a FAILED+=1
)

REM 4. Check static directory
echo Checking static files...
if exist "static\" (
    echo [OK] Static directory exists
    set /a PASSED+=1
) else (
    echo [FAIL] Static directory NOT found
    set /a FAILED+=1
)

REM 5. Check static files
echo Checking individual static files...
if exist "static\style.css" (
    echo [OK] style.css exists
    set /a PASSED+=1
) else (
    echo [FAIL] style.css NOT found
    set /a FAILED+=1
)

if exist "static\app.js" (
    echo [OK] app.js exists
    set /a PASSED+=1
) else (
    echo [FAIL] app.js NOT found
    set /a FAILED+=1
)

if exist "static\nav.js" (
    echo [OK] nav.js exists
    set /a PASSED+=1
) else (
    echo [FAIL] nav.js NOT found
    set /a FAILED+=1
)

if exist "static\favicon.svg" (
    echo [OK] favicon.svg exists
    set /a PASSED+=1
) else (
    echo [FAIL] favicon.svg NOT found
    set /a FAILED+=1
)

REM 6. Check templates directory
echo Checking templates...
if exist "templates\" (
    echo [OK] Templates directory exists
    set /a PASSED+=1
) else (
    echo [FAIL] Templates directory NOT found
    set /a FAILED+=1
)

REM 7. Check critical templates
echo Checking template files...
if exist "templates\base.html" (
    echo [OK] base.html exists
    set /a PASSED+=1
) else (
    echo [FAIL] base.html NOT found
    set /a FAILED+=1
)

if exist "templates\downloader.html" (
    echo [OK] downloader.html exists
    set /a PASSED+=1
) else (
    echo [FAIL] downloader.html NOT found
    set /a FAILED+=1
)

REM 8. Check main.py
echo Checking main application file...
if exist "main.py" (
    echo [OK] main.py exists
    set /a PASSED+=1
) else (
    echo [FAIL] main.py NOT found
    set /a FAILED+=1
)

REM 9. Check FFmpeg
echo Checking FFmpeg...
where ffmpeg >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] FFmpeg installed
    set /a PASSED+=1
) else (
    echo [WARN] FFmpeg not found - required for MP3 downloads
)

REM 10. Check yt-dlp
echo Checking yt-dlp...
where yt-dlp >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] yt-dlp command available
) else (
    echo [WARN] yt-dlp not in PATH
)

REM 11. Check .env file
echo Checking environment configuration...
if exist ".env" (
    echo [OK] .env file exists
    set /a PASSED+=1
) else (
    echo [WARN] .env file not found
)

REM 12. Test Python imports
echo Testing Python imports...
python -c "import fastapi, uvicorn, yt_dlp, jinja2" 2>nul
if %errorlevel% equ 0 (
    echo [OK] Required Python packages installed
    set /a PASSED+=1
) else (
    echo [FAIL] Some Python packages MISSING
    echo Run: pip install -r requirements.txt
    set /a FAILED+=1
)

REM 13. Check deployment files
echo Checking deployment configurations...
if exist "Dockerfile" (
    echo [OK] Dockerfile found
)
if exist "docker-compose.yml" (
    echo [OK] docker-compose.yml found
)
if exist "DEPLOYMENT.md" (
    echo [OK] DEPLOYMENT.md found
)

echo.
echo ==================================
echo Summary
echo ==================================
echo Passed: %PASSED%
echo Failed: %FAILED%
echo.

if %FAILED% equ 0 (
    echo [SUCCESS] All critical checks passed!
    echo Ready for deployment.
    exit /b 0
) else (
    echo [ERROR] Some checks failed.
    echo Please fix the issues above before deploying.
    exit /b 1
)
