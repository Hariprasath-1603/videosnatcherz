# Production Deployment Guide

## Pre-Deployment Checklist

### 1. **Verify Static Files**
Before deploying, ensure all static files are present:

```bash
# Check if static directory exists with all files
ls -la static/
# Should contain: style.css, app.js, nav.js, favicon.svg
```

### 2. **Update Environment Variables**
Create a `.env` file in production:

```bash
ENV=production
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Email configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-production-email@gmail.com
SMTP_PASSWORD=your-app-password

# Optional: Static version for cache busting
STATIC_VERSION=1.0.1
```

### 3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 4. **Test Locally Before Deployment**
```bash
# Test in production mode locally
ENV=production uvicorn main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000` and verify:
- [ ] CSS loads correctly (check browser DevTools Network tab)
- [ ] JavaScript loads correctly
- [ ] Fonts display properly
- [ ] All pages render correctly
- [ ] No 404 errors for static files

---

## Deployment Options

### Option 1: Direct Uvicorn (Simple)

```bash
# Development
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production
ENV=production uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Option 2: Uvicorn with Config File (Recommended)

```bash
ENV=production uvicorn main:app --config uvicorn_config.py
```

### Option 3: Gunicorn + Uvicorn Workers (Production)

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
ENV=production gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile -
```

### Option 4: Docker (Containerized)

See `Dockerfile` for containerized deployment.

### Option 5: Behind Nginx (Recommended for Production)

Nginx configuration for reverse proxy:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;

    # Static files - served directly by Nginx (better performance)
    location /static/ {
        alias /path/to/your/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # For Server-Sent Events (progress tracking)
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
    }
}
```

---

## Cloud Platform Deployments

### Railway.app

1. Create `railway.toml`:
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
restartPolicyType = "on-failure"
restartPolicyMaxRetries = 10
```

2. Set environment variables in Railway dashboard
3. Deploy: `railway up`

### Render.com

1. Create `render.yaml`:
```yaml
services:
  - type: web
    name: youtube-downloader
    env: python
    buildCommand: "pip install -r requirements.txt"
    startCommand: "uvicorn main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: ENV
        value: production
      - key: PYTHON_VERSION
        value: 3.10
```

2. Connect your GitHub repo
3. Deploy automatically on push

### Heroku

1. Create `Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

2. Create `runtime.txt`:
```
python-3.10
```

3. Deploy:
```bash
heroku create your-app-name
git push heroku main
```

### DigitalOcean App Platform

1. Use the web UI to connect your GitHub repo
2. Set build command: `pip install -r requirements.txt`
3. Set run command: `uvicorn main:app --host 0.0.0.0 --port 8080`
4. Set environment variables in the UI

### AWS EC2 / VPS

1. Install dependencies:
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx ffmpeg
```

2. Clone and setup:
```bash
git clone <your-repo>
cd YT-DOWNLOADER
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Create systemd service `/etc/systemd/system/ytdownloader.service`:
```ini
[Unit]
Description=YouTube Downloader FastAPI App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/YT-DOWNLOADER
Environment="PATH=/path/to/YT-DOWNLOADER/.venv/bin"
Environment="ENV=production"
ExecStart=/path/to/YT-DOWNLOADER/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 4

[Install]
WantedBy=multi-user.target
```

4. Enable and start:
```bash
sudo systemctl enable ytdownloader
sudo systemctl start ytdownloader
```

---

## Troubleshooting Static Files

### Issue: CSS/JS Not Loading (404 Errors)

**Check:**
1. Verify files exist in `static/` directory
2. Check file permissions: `chmod -R 755 static/`
3. Verify FastAPI logs show static mount: `INFO: Mounted static files at /static`

**Test static file access directly:**
```bash
curl http://your-domain.com/static/style.css
# Should return CSS content, not 404
```

### Issue: Old CSS Cached in Browser

**Solutions:**
1. Hard refresh: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)
2. Clear browser cache
3. Use incognito/private mode to test
4. Implement cache busting (see below)

**Cache Busting:**
Update version in templates:
```html
<link rel="stylesheet" href="/static/style.css?v=1.0.1" />
<script src="/static/app.js?v=1.0.1"></script>
```

### Issue: Fonts Not Loading

**Check:**
1. Verify Google Fonts URL in base.html
2. Check CORS policy allows fonts
3. Test fonts load: Open DevTools → Network → Filter by "Font"

### Issue: Icons/SVGs Not Displaying

**Check:**
1. Verify favicon.svg exists in static/
2. Check MIME type in response headers should be `image/svg+xml`
3. Clear browser cache

---

## Performance Optimization

### 1. Enable Gzip Compression
```python
# In main.py, add:
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 2. Use CDN for Static Files
Consider using a CDN like Cloudflare, AWS CloudFront, or BunnyCDN for static assets in high-traffic scenarios.

### 3. Minify CSS/JS
```bash
# Install minifiers
npm install -g clean-css-cli uglify-js

# Minify CSS
cleancss -o static/style.min.css static/style.css

# Minify JS
uglifyjs static/app.js -o static/app.min.js -c -m
```

Update templates to use `.min.css` and `.min.js` files.

---

## Security Checklist

- [ ] Set strong SECRET_KEY environment variable
- [ ] Use HTTPS in production (SSL/TLS certificate)
- [ ] Set proper CORS origins (don't use "*" in production)
- [ ] Keep dependencies updated: `pip install --upgrade -r requirements.txt`
- [ ] Use environment variables for sensitive data (never commit .env)
- [ ] Enable rate limiting for API endpoints
- [ ] Implement proper error handling (don't expose stack traces)
- [ ] Disable FastAPI docs in production (/docs, /redoc)

---

## Monitoring & Logging

### View Logs
```bash
# If using systemd
sudo journalctl -u ytdownloader -f

# If running directly
# Logs will appear in terminal
```

### Health Check Endpoint
The app includes basic health checks at `/` (homepage).

Consider adding a dedicated health endpoint:
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
```

---

## Post-Deployment Verification

1. **Visit Homepage:** Should load with all styles
2. **Test Download:** Paste a YouTube URL and download
3. **Check Network Tab:** No 404 errors for static files
4. **Test All Pages:** Home, Downloader, Features, About, FAQ, Contact
5. **Mobile Test:** Responsive design works on mobile
6. **Performance Test:** Check page load times

---

## Rollback Procedure

If deployment fails:

1. **Quick Rollback:**
```bash
git revert HEAD
git push
# Redeploy
```

2. **Full Rollback:**
```bash
git checkout <previous-working-commit>
# Redeploy
```

---

## Support

If issues persist:
1. Check browser DevTools Console for JavaScript errors
2. Check browser DevTools Network tab for failed requests
3. Check server logs for Python errors
4. Test in incognito mode to rule out caching issues
5. Verify environment variables are set correctly

Remember: Static files paths must be absolute (start with `/`) in templates!
