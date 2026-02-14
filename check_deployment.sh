#!/bin/bash

# Production Deployment Verification Script
# Run this before deploying to catch common issues

set -e  # Exit on error

echo "=================================="
echo "Pre-Deployment Checklist"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check counter
PASSED=0
FAILED=0

# Function to check status
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} $1"
        ((FAILED++))
    fi
}

# 1. Check Python version
echo "Checking Python version..."
python --version | grep -q "Python 3" && check "Python 3.x installed" || check "Python 3.x NOT found"

# 2. Check if virtual environment exists
echo "Checking virtual environment..."
if [ -d ".venv" ] || [ -d "venv" ]; then
    check "Virtual environment found"
else
    echo -e "${YELLOW}!${NC} Virtual environment not found (optional but recommended)"
fi

# 3. Check if requirements.txt exists
echo "Checking requirements.txt..."
[ -f "requirements.txt" ] && check "requirements.txt exists" || check "requirements.txt NOT found"

# 4. Check if static directory exists
echo "Checking static files..."
[ -d "static" ] && check "Static directory exists" || check "Static directory NOT found"

# 5. Check if static files exist
echo "Checking individual static files..."
[ -f "static/style.css" ] && check "style.css exists" || check "style.css NOT found"
[ -f "static/app.js" ] && check "app.js exists" || check "app.js NOT found"
[ -f "static/nav.js" ] && check "nav.js exists" || check "nav.js NOT found"
[ -f "static/favicon.svg" ] && check "favicon.svg exists" || check "favicon.svg NOT found"

# 6. Check if templates directory exists
echo "Checking templates..."
[ -d "templates" ] && check "Templates directory exists" || check "Templates directory NOT found"

# 7. Check critical template files
echo "Checking template files..."
[ -f "templates/base.html" ] && check "base.html exists" || check "base.html NOT found"
[ -f "templates/downloader.html" ] && check "downloader.html exists" || check "downloader.html NOT found"

# 8. Check for absolute paths in templates
echo "Checking for absolute paths in templates..."
if grep -q 'href="/static/' templates/base.html && grep -q 'src="/static/' templates/base.html; then
    check "Templates use absolute paths (/static/)"
else
    check "Templates may have incorrect paths"
fi

# 9. Check main.py exists
echo "Checking main application file..."
[ -f "main.py" ] && check "main.py exists" || check "main.py NOT found"

# 10. Check if FFmpeg is installed (required for MP3 conversion)
echo "Checking FFmpeg..."
command -v ffmpeg >/dev/null 2>&1 && check "FFmpeg installed" || echo -e "${YELLOW}!${NC} FFmpeg not found (required for MP3 downloads)"

# 11. Check if yt-dlp is accessible
echo "Checking yt-dlp..."
command -v yt-dlp >/dev/null 2>&1 && check "yt-dlp command available" || echo -e "${YELLOW}!${NC} yt-dlp command not in PATH (optional)"

# 12. Check if .env file exists
echo "Checking environment configuration..."
if [ -f ".env" ]; then
    check ".env file exists"
    # Check if critical env vars are set
    if grep -q "SMTP_USERNAME" .env && grep -q "SMTP_PASSWORD" .env; then
        check "Email configuration found in .env"
    else
        echo -e "${YELLOW}!${NC} Email configuration incomplete in .env"
    fi
else
    echo -e "${YELLOW}!${NC} .env file not found (create from .env.example)"
fi

# 13. Test Python imports
echo "Testing Python imports..."
python -c "import fastapi, uvicorn, yt_dlp, jinja2" 2>/dev/null && check "Required Python packages installed" || check "Some Python packages MISSING - run: pip install -r requirements.txt"

# 14. Check static file permissions
echo "Checking file permissions..."
if [ -r "static/style.css" ] && [ -r "static/app.js" ]; then
    check "Static files are readable"
else
    check "Static files may have permission issues"
fi

# 15. Check for common deployment files
echo "Checking deployment configurations..."
[ -f "Dockerfile" ] && echo -e "${GREEN}✓${NC} Dockerfile found" || echo -e "${YELLOW}!${NC} Dockerfile not found (optional)"
[ -f "docker-compose.yml" ] && echo -e "${GREEN}✓${NC} docker-compose.yml found" || echo -e "${YELLOW}!${NC} docker-compose.yml not found (optional)"
[ -f "DEPLOYMENT.md" ] && echo -e "${GREEN}✓${NC} DEPLOYMENT.md found" || echo -e "${YELLOW}!${NC} DEPLOYMENT.md not found"

echo ""
echo "=================================="
echo "Summary"
echo "=================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All critical checks passed!${NC}"
    echo "Ready for deployment."
    exit 0
else
    echo -e "${RED}✗ Some checks failed.${NC}"
    echo "Please fix the issues above before deploying."
    exit 1
fi
