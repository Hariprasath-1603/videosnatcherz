# Contact Form Email Setup Guide

## Gmail Configuration (Recommended)

The contact form sends emails to **hariprasath16032006@gmail.com** using Gmail's SMTP server.

### Step-by-Step Setup

#### 1. Enable 2-Step Verification

1. Go to your Google Account: https://myaccount.google.com
2. Click **Security** in left menu
3. Under "Signing in to Google", click **2-Step Verification**
4. Follow the prompts to set it up

#### 2. Generate App Password

1. Go to App Passwords: https://myaccount.google.com/apppasswords
2. Sign in if prompted
3. Select app: **Mail**
4. Select device: **Windows Computer** (or your OS)
5. Click **Generate**
6. **Copy the 16-character password** (e.g., `abcd efgh ijkl mnop`)

#### 3. Create `.env` File

In your project root directory (`d:\PROJECTS\YT DOWNLOADER`), create a file named `.env`:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
```

**Replace:**
- `your-email@gmail.com` with your actual Gmail address
- `abcdefghijklmnop` with your App Password (remove spaces)

**Example `.env` file:**
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=myemail@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
```

#### 4. Test the Setup

1. **Restart the server** (important to load new env vars):
   ```bash
   uvicorn main:app --reload
   ```
   Or double-click `start.bat`

2. Go to: http://127.0.0.1:8000/contact

3. Fill out the form with test data

4. Click **Send Message**

5. Check **hariprasath16032006@gmail.com** inbox

## Alternative: Using Other Email Providers

### Outlook/Hotmail

```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
```

### Yahoo Mail

```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USERNAME=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

### Custom SMTP Server

```env
SMTP_SERVER=mail.yourserver.com
SMTP_PORT=587
SMTP_USERNAME=noreply@yourserver.com
SMTP_PASSWORD=your-password
```

## Security Best Practices

✅ **DO:**
- Use App Passwords, never your real Gmail password
- Keep `.env` file local (already in `.gitignore`)
- Use environment variables in production
- Revoke App Password if compromised

❌ **DON'T:**
- Commit `.env` to Git
- Share your App Password
- Use regular password for SMTP
- Hardcode credentials in source code

## Troubleshooting

### "SMTP authentication error"
- Double-check username and password
- Ensure 2-Step Verification is enabled
- Regenerate App Password

### "Connection refused" or "Timeout"
- Check firewall settings
- Verify port 587 is not blocked
- Try port 465 with SSL (change code accordingly)

### Email not received
- Check spam/junk folder
- Verify `RECIPIENT_EMAIL` in `main.py` is correct
- Check Gmail "Sent" folder of SMTP_USERNAME account

### "Service not configured" error
- `.env` file not loaded
- Restart server after creating `.env`
- Check environment variables: `echo $env:SMTP_USERNAME` (PowerShell)

## Loading Environment Variables

### Windows PowerShell
The `start.bat` file automatically loads `.env`.

Or manually:
```powershell
Get-Content .env | ForEach-Object {
    $name, $value = $_.split('=')
    Set-Content env:\$name $value
}
uvicorn main:app --reload
```

### Linux/Mac
The `start.sh` file automatically loads `.env`.

Or manually:
```bash
export $(grep -v '^#' .env | xargs)
uvicorn main:app --reload
```

## Production Deployment

For production servers:

1. **Never use `.env` files** - Use proper environment variable management
2. **Cloud platforms** (Heroku, Vercel, AWS):
   - Set env vars in dashboard/settings
   - Use secrets management services
3. **Docker:**
   ```yaml
   environment:
     - SMTP_SERVER=smtp.gmail.com
     - SMTP_USERNAME=${SMTP_USERNAME}
     - SMTP_PASSWORD=${SMTP_PASSWORD}
   ```

## Testing Without Email Setup

If you don't want to configure email, the contact form will show:
> "Email service not configured. Please contact the administrator directly."

Users can still see your email address in the Contact page and reach out manually.

---

**Questions?** Check the main [README.md](README.md) or [SETUP.md](SETUP.md) for more help.
