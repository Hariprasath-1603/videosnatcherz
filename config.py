"""
Production Configuration for YouTube Downloader
"""
import os
from pathlib import Path

# Environment
ENV = os.environ.get("ENV", "development")
IS_PRODUCTION = ENV == "production"
DEBUG = not IS_PRODUCTION

# Paths
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Server Configuration
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
WORKERS = int(os.environ.get("WORKERS", "4"))

# Static Files Version (for cache busting)
# Update this when deploying new CSS/JS changes
STATIC_VERSION = os.environ.get("STATIC_VERSION", "1.0.0")

# Email Configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "hariprasath16032006@gmail.com")

# Security
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO" if IS_PRODUCTION else "DEBUG")

# Feature Flags
ENABLE_DOCS = not IS_PRODUCTION
ENABLE_CORS = True

# Cache Settings
STATIC_CACHE_MAX_AGE = 31536000 if IS_PRODUCTION else 0  # 1 year in production, no cache in dev
