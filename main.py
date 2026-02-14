import asyncio
import os
import re
import shutil
import smtplib
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import TemplateNotFound
import yt_dlp

app = FastAPI(
    title="YouTube Downloader",
    description="Download YouTube videos or audio for personal/educational use only.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates_dir = Path("templates")

# Email configuration (use environment variables for security)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
RECIPIENT_EMAIL = "hariprasath16032006@gmail.com"


def validate_video_url(url: str) -> bool:
    """Validate if URL is from a supported video platform."""
    if not url or not url.strip():
        return False
    
    # Check for supported video platforms
    valid_patterns = [
        r'(youtube\.com|youtu\.be)',
        r'vimeo\.com',
        r'dailymotion\.com',
        r'twitch\.tv'
    ]
    
    url_lower = url.lower()
    return any(re.search(pattern, url_lower) for pattern in valid_patterns)


def build_format_selector(quality: Optional[int]) -> str:
    """Build yt-dlp format selector respecting an optional max height."""
    if quality:
        return f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"
    return "bestvideo+bestaudio/best"


def download_media(url: str, media_format: str, quality: Optional[int], audio_quality: Optional[int] = None) -> Tuple[Path, str]:
    """Download media with yt-dlp and return the file path and temp dir used."""
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    
    tmpdir = tempfile.mkdtemp(prefix="ytdl_")
    outtmpl = str(Path(tmpdir) / "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "restrictfilenames": True,
        "windowsfilenames": True,
        "quiet": True,
    }

    if media_format == "mp3":
        bitrate = str(audio_quality) if audio_quality else "192"
        ydl_opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": bitrate,
                    }
                ],
            }
        )
    else:
        ydl_opts.update(
            {
                "format": build_format_selector(quality),
                "merge_output_format": "mp4",
            }
        )

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        error_msg = str(exc)
        if "ERROR:" in error_msg:
            # Extract just the relevant error message
            error_msg = error_msg.split("ERROR:")[-1].strip()
        if "ffmpeg" in error_msg.lower() or "postprocess" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail="FFmpeg is required for this format. Please ensure FFmpeg is installed."
            ) from exc
        elif "private" in error_msg.lower() or "available" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Video is unavailable, private, or region-restricted."
            ) from exc
        else:
            raise HTTPException(
                status_code=400,
                detail="Unable to download video. Please check the URL and try again."
            ) from exc
    except Exception as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during download. Please try again."
        ) from exc

    target_ext = "mp3" if media_format == "mp3" else "mp4"
    files = list(Path(tmpdir).glob(f"*.{target_ext}"))
    if not files:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="No output file produced.")

    return files[0], tmpdir


def extract_metadata(url: str) -> Dict[str, Optional[str]]:
    """Extract minimal metadata without downloading the media."""
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    
    ydl_opts ={"quiet": True,
        "noplaylist": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        error_msg = str(exc)
        if "ERROR:" in error_msg:
            error_msg = error_msg.split("ERROR:")[-1].strip()
        if "private" in error_msg.lower() or "available" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Video is unavailable, private, or region-restricted."
            ) from exc
        else:
            raise HTTPException(
                status_code=400,
                detail="Unable to fetch video information. Please check the URL."
            ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching video info."
        ) from exc

    thumbnail = info.get("thumbnail")
    if not thumbnail:
        thumbnails = info.get("thumbnails") or []
        thumbnail = thumbnails[-1]["url"] if thumbnails else None

    return {
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail": thumbnail,
        "uploader": info.get("uploader"),
        "webpage_url": info.get("webpage_url"),
    }


from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/downloader", response_class=HTMLResponse)
async def downloader_page(request: Request):
    return templates.TemplateResponse("downloader.html", {"request": request})


@app.get("/features", response_class=HTMLResponse)
async def features(request: Request):
    return templates.TemplateResponse("features.html", {"request": request})


@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


@app.get("/faq", response_class=HTMLResponse)
async def faq(request: Request):
    return templates.TemplateResponse("faq.html", {"request": request})


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})


@app.post("/api/download")
async def download(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    media_format: str = Form("mp4"),
    quality: Optional[int] = Form(None),
    audio_quality: Optional[int] = Form(None),
):
    # Validate inputs
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL is required.")
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    if media_format not in {"mp4", "mp3"}:
        raise HTTPException(status_code=400, detail="Format must be 'mp4' or 'mp3'.")
    if quality is not None and quality <= 0:
        raise HTTPException(status_code=400, detail="Quality must be a positive integer.")
    if audio_quality is not None and audio_quality <= 0:
        raise HTTPException(status_code=400, detail="Audio quality must be a positive integer.")

    file_path, tmpdir = await asyncio.to_thread(download_media, url, media_format, quality, audio_quality)
    background_tasks.add_task(shutil.rmtree, tmpdir, True)

    media_type = "audio/mpeg" if media_format == "mp3" else "video/mp4"
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
    )


@app.get("/api/metadata")
async def metadata(url: str):
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL is required.")
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    return await asyncio.to_thread(extract_metadata, url)


@app.post("/api/contact")
async def contact_form(
    name: str = Form(...),
    email: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
):
    """Handle contact form submissions and send email."""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="Email service not configured. Please contact the administrator directly.",
        )

    try:
        # Create email message
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{name} <{SMTP_USERNAME}>"
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = f"[YT Downloader Contact] {subject}"
        msg["Reply-To"] = email

        # Email body
        text_body = f"""
New contact form submission from YT Downloader

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}

---
This message was sent via the YT Downloader contact form.
Reply directly to {email} to respond.
"""

        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #22c55e;">New Contact Form Submission</h2>
    <p><strong>From:</strong> {name} ({email})</p>
    <p><strong>Subject:</strong> {subject}</p>
    <hr style="border: 1px solid #e2e8f0;">
    <h3>Message:</h3>
    <p>{message.replace(chr(10), '<br>')}</p>
    <hr style="border: 1px solid #e2e8f0;">
    <p style="color: #64748b; font-size: 14px;">
        This message was sent via the YT Downloader contact form.<br>
        Reply directly to <a href="mailto:{email}">{email}</a> to respond.
    </p>
</body>
</html>
"""

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send email
        await asyncio.to_thread(_send_email, msg)

        return {"message": "Message sent successfully! We'll get back to you soon."}

    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to send email: {str(exc)}"
        ) from exc


def _send_email(msg: MIMEMultipart):
    """Send email using SMTP (blocking operation)."""
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
