# YouTube Downloader - Setup Instructions

## Quick Start

1. **Install Python 3.10+** and **FFmpeg**

2. **Clone/Download the project**

3. **Create virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```

6. **Open browser:** http://127.0.0.1:8000

## Email Configuration (for Contact Form)

### Gmail Setup

1. **Enable 2-Step Verification** on your Google Account
2. **Create App Password:**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and your device
   - Copy the 16-character password

3. **Create `.env` file** in project root:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-16-char-app-password
   ```

4. **Restart the server** to load environment variables

### Testing Contact Form

1. Go to http://127.0.0.1:8000/contact
2. Fill out the form
3. Submit
4. Check hariprasath16032006@gmail.com for the message

## YouTube Download Issues

If downloads fail with "INNERTUBE_CONTEXT" or similar errors:

### Solution 1: Update yt-dlp
```bash
pip install -U yt-dlp
```

### Solution 2: Use Cookies
1. Install browser extension "Get cookies.txt LOCALLY"
2. Go to youtube.com (logged in)
3. Export cookies to `cookies.txt`
4. In `.env` file:
   ```
   YTDL_COOKIES=path/to/cookies.txt
   ```
5. Restart server

## FFmpeg Installation

### Windows
```powershell
winget install ffmpeg
```

### Linux
```bash
sudo apt install ffmpeg
```

### Mac
```bash
brew install ffmpeg
```

Verify installation:
```bash
ffmpeg -version
```

## Deployment Checklist

Before deploying to production:

- [ ] Set all environment variables securely
- [ ] Tighten CORS policy in `main.py`
- [ ] Enable HTTPS
- [ ] Add rate limiting
- [ ] Review privacy policy
- [ ] Test contact form
- [ ] Test video downloads
- [ ] Configure domain/hosting
- [ ] Set up monitoring/logging

## Common Errors

### "Script execution disabled"
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### "Module not found"
- Ensure venv is activated
- Run `pip install -r requirements.txt`

### "Port already in use"
- Change port: `uvicorn main:app --port 8001 --reload`
- Or kill existing process

## Project Structure Reference

```
YT DOWNLOADER/
├── main.py              # Backend API
├── requirements.txt     # Dependencies
├── .env.example        # Environment template
├── .env                # Your config (create this)
├── templates/          # HTML pages
│   ├── base.html
│   ├── home.html
│   ├── downloader.html
│   └── ...
└── static/            # CSS, JS, images
    ├── style.css
    ├── app.js
    ├── nav.js
    └── favicon.svg
```

## Support

- Check [README.md](README.md) for full documentation
- Visit [FAQ page](http://127.0.0.1:8000/faq) for common questions
- Use contact form for issues

---

**Remember:** This tool is for educational and personal use only. Respect copyright laws and YouTube's Terms of Service.
