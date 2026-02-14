"""
Uvicorn Production Configuration
Usage: uvicorn main:app --config uvicorn_config.py
"""

# Server Socket
bind = "0.0.0.0:8000"

# Worker Processes
workers = 4  # Adjust based on CPU cores: 2 * CPU_CORES + 1
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
loglevel = "info"
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Performance
keepalive = 65
timeout = 300  # 5 minutes for large video downloads
worker_connections = 1000
max_requests = 10000
max_requests_jitter = 1000

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# Process Naming
proc_name = "youtube-downloader"

# SSL (if using HTTPS directly with Uvicorn)
# keyfile = "/path/to/ssl/key.pem"
# certfile = "/path/to/ssl/cert.pem"
