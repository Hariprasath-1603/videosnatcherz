# Quick Deployment Reference Card

## ✅ Pre-Deployment Checklist

Run verification script:
```bash
# Windows
check_deployment.bat

# Linux/Mac
chmod +x check_deployment.sh
./check_deployment.sh
```

## 🚀 Quick Start Commands

### Local Development
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Simple)
```bash
ENV=production uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Production (With Config)
```bash
ENV=production uvicorn main:app --config uvicorn_config.py
```

### Docker
```bash
# Build
docker build -t youtube-downloader .

# Run
docker run -p 8000:8000 -e ENV=production youtube-downloader

# Or use docker-compose
docker-compose up -d
```

## 🔍 Verify Deployment

1. **Check homepage loads:**
   ```
   curl http://your-domain.com/
   ```

2. **Check static files:**
   ```
   curl http://your-domain.com/static/style.css
   curl http://your-domain.com/static/app.js
   ```

3. **Browser DevTools:**
   - Open F12 → Network tab
   - Reload page
   - Check for 404 errors
   - Verify all assets load (green status codes)

## 🐛 Common Issues & Fixes

### Issue: CSS Not Loading (404)
**Fix:**
- Verify `static/` directory exists
- Check file permissions: `chmod -R 755 static/`
- Verify templates use `/static/` (absolute path)
- Clear browser cache (Ctrl+F5)

### Issue: Old Styles Cached
**Fix:**
- Update version in templates: `style.css?v=1.1.1`
- Clear browser cache
- Test in incognito mode

### Issue: Fonts Not Loading
**Fix:**
- Check Google Fonts URL in `base.html`
- Verify internet connection on server
- Check for font CDN blocks

### Issue: Internal Server Error
**Fix:**
- Check logs: `journalctl -u ytdownloader -f`
- Verify environment variables are set
- Check Python dependencies installed
- Verify FFmpeg is installed for MP3

## 📝 Environment Variables

Required for production:
```bash
ENV=production
HOST=0.0.0.0
PORT=8000
WORKERS=4
```

Optional (for email):
```bash
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 🔄 Update Deployment

1. **Pull latest code:**
   ```bash
   git pull origin main
   ```

2. **Update dependencies:**
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. **Update static version** (if CSS/JS changed):
   - Edit `templates/base.html`
   - Change `?v=1.0.0` to `?v=1.0.1`

4. **Restart service:**
   ```bash
   # Systemd
   sudo systemctl restart ytdownloader
   
   # Docker
   docker-compose restart
   
   # Direct
   # Kill process and restart uvicorn
   ```

## 🔒 Security Checklist

- [ ] HTTPS enabled (SSL certificate)
- [ ] CORS configured (not `*` in production)
- [ ] Environment variables not in code
- [ ] `.env` not committed to git
- [ ] Strong SECRET_KEY set
- [ ] FastAPI docs disabled (`/docs`, `/redoc`)
- [ ] Firewall configured (only 80/443 open)
- [ ] Regular updates (`pip install --upgrade`)

## 📊 Monitoring

Check application health:
```bash
# Logs
journalctl -u ytdownloader -f

# Process status
systemctl status ytdownloader

# Port listening
netstat -tlnp | grep 8000

# Disk space
df -h
```

## 🆘 Emergency Rollback

```bash
# Revert to previous version
git log --oneline  # Find commit hash
git checkout <previous-commit-hash>

# Restart service
sudo systemctl restart ytdownloader
```

## 📱 Contact for Issues

If issues persist after following this guide:
1. Check all logs for error messages
2. Test in local development mode first
3. Verify all environment variables
4. Review DEPLOYMENT.md for detailed guide
