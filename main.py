import asyncio
import json
import os
import re
import shutil
import smtplib
import subprocess
import tempfile
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Optional, Tuple, AsyncGenerator
from urllib.parse import quote

from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import TemplateNotFound
import yt_dlp

# Determine if running in production
IS_PRODUCTION = os.environ.get("ENV", "development") == "production"

app = FastAPI(
    title="YouTube Downloader",
    description="Download YouTube videos or audio for personal/educational use only.",
    version="0.1.0",
    docs_url=None if IS_PRODUCTION else "/docs",  # Disable docs in production
    redoc_url=None if IS_PRODUCTION else "/redoc",
)

# Enable Gzip compression for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files with proper configuration
# html=True allows serving index.html files from directories
app.mount("/static", StaticFiles(directory="static", html=False), name="static")

# Add static file cache headers for production
@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add cache headers for static files in production
    if request.url.path.startswith("/static/"):
        if IS_PRODUCTION:
            # Cache static files for 1 year in production
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            # No cache in development for easier debugging
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
    
    # Security headers for all responses
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    return response

templates_dir = Path("templates")

# Email configuration (use environment variables for security)
# Titan Email SMTP with SSL
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.titan.email")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))  # SSL port
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", "info@videosnatcherz.tech")

# Global dictionary to store download progress
download_progress: Dict[str, Dict] = {}


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


def build_format_selector(quality: Optional[int], prefer_progressive: bool = True) -> str:
    """Build yt-dlp format selector respecting an optional max height.
    
    Args:
        quality: Maximum video height (e.g., 1080 for 1080p)
        prefer_progressive: If True, prefer progressive formats that don't need merging
    """
    if prefer_progressive:
        # Progressive formats are single-file MP4s that don't need audio/video merging
        # This significantly speeds up downloads
        if quality:
            return f"best[height<={quality}][ext=mp4]/bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"
        return "best[ext=mp4]/bestvideo+bestaudio/best"
    else:
        # Original format selector (may require merging)
        if quality:
            return f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"
        return "bestvideo+bestaudio/best"


def download_media(url: str, media_format: str, quality: Optional[int], audio_quality: Optional[int] = None, download_id: Optional[str] = None) -> Tuple[Path, str]:
    """Download media with yt-dlp and return the file path and temp dir used."""
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    
    tmpdir = tempfile.mkdtemp(prefix="ytdl_")
    outtmpl = str(Path(tmpdir) / "%(title)s.%(ext)s")

    def progress_hook(d):
        """Hook to track download progress."""
        if download_id:
            if d['status'] == 'downloading':
                # Extract progress information
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                
                if total > 0:
                    percentage = int((downloaded / total) * 100)
                    download_progress[download_id] = {
                        'status': 'downloading',
                        'percentage': percentage,
                        'downloaded': downloaded,
                        'total': total,
                        'speed': d.get('speed', 0),
                        'eta': d.get('eta', 0)
                    }
                else:
                    download_progress[download_id] = {
                        'status': 'downloading',
                        'percentage': 0,
                        'downloaded': downloaded
                    }
            elif d['status'] == 'finished':
                # Download finished, now processing
                download_progress[download_id] = {
                    'status': 'processing',
                    'percentage': 100
                }

    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "restrictfilenames": True,
        "windowsfilenames": True,
        "quiet": True,
        "progress_hooks": [progress_hook],
    }

    if media_format == "mp3":
        # MP3 with FFmpeg conversion - best compatibility but slower
        bitrate = str(audio_quality) if audio_quality else "192"
        ydl_opts.update(
            {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": bitrate,
                    }
                ],
            }
        )
    elif media_format == "m4a":
        # Direct M4A audio - no conversion needed, instant download
        ydl_opts.update(
            {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "postprocessors": [],
            }
        )
    else:
        ydl_opts.update(
            {
                "format": build_format_selector(quality, prefer_progressive=True),
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

    # Determine target file extension
    if media_format == "mp3":
        target_ext = "mp3"
    elif media_format == "m4a":
        target_ext = "m4a"
    else:
        target_ext = "mp4"
    
    files = list(Path(tmpdir).glob(f"*.{target_ext}"))
    if not files:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="No output file produced.")

    return files[0], tmpdir


async def stream_audio_download(url: str, media_format: str, audio_quality: Optional[int]) -> Tuple[AsyncGenerator, str]:
    """Stream audio download with real-time conversion for instant start.
    
    Returns an async generator that yields audio data chunks as they're processed,
    and a suggested filename.
    """
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    
    # Get video info to extract direct URL and filename
    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "restrictfilenames": True,
        "windowsfilenames": True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        # Get direct audio URL
        audio_url = info.get("url")
        if not audio_url and info.get("requested_downloads"):
            audio_url = info["requested_downloads"][0].get("url")
        
        if not audio_url:
            raise HTTPException(status_code=500, detail="Could not extract audio URL.")
        
        # Get safe filename - ensure ASCII-only for HTTP headers
        title = info.get("title", "audio")
        # Remove non-ASCII and keep only safe characters
        safe_title = "".join(c if c.isascii() and (c.isalnum() or c in (' ', '-', '_')) else '_' for c in title).strip()
        # Replace multiple spaces/underscores with single ones
        safe_title = re.sub(r'[\s_]+', '_', safe_title)
        safe_title = safe_title[:100] or "audio"  # Fallback if empty
        
        if media_format == "mp3":
            # For MP3, we need FFmpeg conversion - fall back to non-streaming for reliability
            raise HTTPException(status_code=501, detail="Streaming not available for MP3. Using standard download.")
        
        else:  # M4A
            # Stream M4A directly without conversion
            filename = f"{safe_title}.m4a"
            
            async def stream_m4a():
                """Stream M4A audio directly using yt-dlp subprocess."""
                # Check if yt-dlp is available
                try:
                    check_proc = await asyncio.create_subprocess_exec(
                        "yt-dlp",
                        "--version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await check_proc.wait()
                    if check_proc.returncode != 0:
                        raise Exception("yt-dlp not found in PATH")
                except Exception as e:
                    raise HTTPException(status_code=500, detail="yt-dlp command not available. Please use standard download.")
                
                ytdlp_cmd = [
                    "yt-dlp",
                    "-f", "bestaudio[ext=m4a]/bestaudio/best",
                    "-o", "-",  # Output to stdout
                    "--no-playlist",
                    "--quiet",
                    "--no-warnings",
                    url
                ]
                
                process = None
                try:
                    process = await asyncio.create_subprocess_exec(
                        *ytdlp_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    # Stream directly to client
                    chunk_size = 64 * 1024  # 64KB chunks
                    while True:
                        chunk = await process.stdout.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
                    
                    await process.wait()
                    
                    if process.returncode != 0:
                        stderr = await process.stderr.read()
                        error_msg = stderr.decode('utf-8', errors='ignore')[:200]
                        raise Exception(f"Download failed: {error_msg}")
                
                except Exception as e:
                    if process:
                        try:
                            process.kill()
                            await process.wait()
                        except:
                            pass
                    raise Exception(f"Streaming failed: {str(e)[:100]}")
            
            return stream_m4a(), filename
    
    except yt_dlp.utils.DownloadError as exc:
        error_msg = str(exc)
        if "ERROR:" in error_msg:
            error_msg = error_msg.split("ERROR:")[-1].strip()
        raise HTTPException(status_code=400, detail="Unable to extract audio. Please check the URL.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Audio preparation failed: {str(exc)[:100]}")


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


def extract_direct_url(url: str, media_format: str, quality: Optional[int], audio_quality: Optional[int]) -> Dict:
    """Extract direct download URL without downloading the file.
    
    This enables instant download start by getting the direct URL from the platform.
    Returns URL, filename, and other metadata.
    """
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    
    ydl_opts = {
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
        "restrictfilenames": True,
        "windowsfilenames": True,
    }
    
    if media_format == "mp3":
        # MP3 requires FFmpeg conversion - must use server-side processing
        return None
    elif media_format == "m4a":
        # M4A can use direct download - instant!
        ydl_opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    else:
        # MP4 video - try to get progressive format
        ydl_opts["format"] = build_format_selector(quality, prefer_progressive=True)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        # Get the direct URL
        direct_url = info.get("url")
        if not direct_url and info.get("requested_downloads"):
            direct_url = info["requested_downloads"][0].get("url")
        
        if not direct_url:
            # No direct URL available, fallback to server download
            return None
        
        # Sanitize filename - ensure ASCII-only for HTTP headers
        title = info.get("title", "audio" if media_format in ["mp3", "m4a"] else "video")
        # Remove non-ASCII and keep only safe characters
        safe_title = "".join(c if c.isascii() and (c.isalnum() or c in (' ', '-', '_')) else '_' for c in title).strip()
        # Replace multiple spaces/underscores with single ones
        safe_title = re.sub(r'[\s_]+', '_', safe_title)
        safe_title = safe_title[:100] or "download"  # Fallback if empty
        
        # Determine extension
        if media_format == "m4a":
            ext = "m4a"
        elif media_format == "mp3":
            ext = "mp3"
        else:
            ext = info.get("ext", "mp4")
        
        filename = f"{safe_title}.{ext}"
        
        return {
            "url": direct_url,
            "filename": filename,
            "title": info.get("title"),
            "filesize": info.get("filesize") or info.get("filesize_approx"),
            "ext": ext,
        }
    
    except yt_dlp.utils.DownloadError as exc:
        error_msg = str(exc)
        if "ERROR:" in error_msg:
            error_msg = error_msg.split("ERROR:")[-1].strip()
        # Return None to fallback to server download
        return None
    except Exception as exc:
        # Return None to fallback to server download
        return None


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


@app.post("/api/stream-audio")
async def stream_audio(
    url: str = Form(...),
    media_format: str = Form("m4a"),
    audio_quality: Optional[int] = Form(None),
):
    """Stream audio download with real-time conversion for instant start.
    
    This endpoint provides Y2Mate/SaveFrom-like instant audio downloads by streaming
    the audio data as it's being processed, rather than waiting for the full file.
    """
    # Validate inputs
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL is required.")
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    if media_format not in {"mp3", "m4a"}:
        raise HTTPException(status_code=400, detail="Format must be 'mp3' or 'm4a' for audio streaming.")
    
    try:
        # Get streaming generator and filename
        stream_generator, filename = await stream_audio_download(url, media_format, audio_quality)
        
        # Return streaming response
        media_type = "audio/mpeg" if media_format == "mp3" else "audio/mp4"
        
        # Encode filename for HTTP header (handle non-ASCII characters)
        # Use ASCII fallback for 'filename' and UTF-8 encoded for 'filename*' (RFC 5987)
        try:
            # Try to encode as ASCII
            ascii_filename = filename.encode('ascii').decode('ascii')
            content_disposition = f'attachment; filename="{ascii_filename}"'
        except (UnicodeEncodeError, UnicodeDecodeError):
            # Contains non-ASCII characters, use RFC 5987 encoding
            ascii_fallback = "audio." + filename.split('.')[-1]  # Simple fallback
            encoded_filename = quote(filename)
            content_disposition = f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded_filename}"
        
        return StreamingResponse(
            stream_generator,
            media_type=media_type,
            headers={
                "Content-Disposition": content_disposition,
                "Cache-Control": "no-cache",
            }
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Audio streaming failed: {str(exc)[:100]}"
        )


@app.post("/api/download")
async def download(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    media_format: str = Form("mp4"),
    quality: Optional[int] = Form(None),
    audio_quality: Optional[int] = Form(None),
    download_id: Optional[str] = Form(None),
):
    # Validate inputs
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL is required.")
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    if media_format not in {"mp4", "mp3", "m4a"}:
        raise HTTPException(status_code=400, detail="Format must be 'mp4', 'mp3', or 'm4a'.")
    if quality is not None and quality <= 0:
        raise HTTPException(status_code=400, detail="Quality must be a positive integer.")
    if audio_quality is not None and audio_quality <= 0:
        raise HTTPException(status_code=400, detail="Audio quality must be a positive integer.")

    # Use provided download ID or generate new one for progress tracking
    if not download_id:
        download_id = str(uuid.uuid4())
    download_progress[download_id] = {'status': 'initializing', 'percentage': 1}
    
    file_path, tmpdir = await asyncio.to_thread(download_media, url, media_format, quality, audio_quality, download_id)
    
    # Mark as complete
    download_progress[download_id] = {'status': 'complete', 'percentage': 100}
    
    # Clean up progress after 60 seconds
    async def cleanup_progress():
        await asyncio.sleep(60)
        download_progress.pop(download_id, None)
    
    background_tasks.add_task(cleanup_progress)
    background_tasks.add_task(shutil.rmtree, tmpdir, True)

    # Set appropriate media type
    if media_format == "mp3":
        media_type = "audio/mpeg"
    elif media_format == "m4a":
        media_type = "audio/mp4"
    else:
        media_type = "video/mp4"
    
    # Sanitize filename to ensure ASCII-only for HTTP headers
    original_filename = file_path.name
    safe_filename = "".join(c if c.isascii() and (c.isalnum() or c in (' ', '-', '_', '.')) else '_' for c in original_filename)
    safe_filename = re.sub(r'[\s_]+', '_', safe_filename) or original_filename
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=safe_filename,
        headers={"X-Download-ID": download_id}
    )


@app.get("/api/progress/{download_id}")
async def progress_stream(download_id: str):
    """Server-Sent Events endpoint for real-time download progress."""
    async def event_generator():
        try:
            # Send initial connection event
            yield f"data: {{'status': 'connected'}}\n\n"
            
            # Stream progress updates
            last_percentage = -1
            timeout_counter = 0
            max_timeout = 300  # 30 seconds (100ms * 300)
            
            while timeout_counter < max_timeout:
                if download_id in download_progress:
                    progress_data = download_progress[download_id]
                    current_percentage = progress_data.get('percentage', 0)
                    
                    # Send update if percentage changed
                    if current_percentage != last_percentage:
                        yield f"data: {json.dumps(progress_data)}\n\n"
                        last_percentage = current_percentage
                    
                    # If complete, send final message and close
                    if progress_data.get('status') == 'complete':
                        yield f"data: {json.dumps({'status': 'complete', 'percentage': 100})}\n\n"
                        break
                    
                    timeout_counter = 0  # Reset timeout when we have data
                else:
                    timeout_counter += 1
                
                await asyncio.sleep(0.1)  # Poll every 100ms
            
            # Timeout or completion
            if timeout_counter >= max_timeout:
                yield f"data: {{'status': 'timeout'}}\n\n"
        
        except asyncio.CancelledError:
            # Client disconnected
            pass
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/metadata")
async def metadata(url: str):
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL is required.")
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    return await asyncio.to_thread(extract_metadata, url)


@app.post("/api/get-download-url")
async def get_download_url(
    url: str = Form(...),
    media_format: str = Form("mp4"),
    quality: Optional[int] = Form(None),
    audio_quality: Optional[int] = Form(None),
):
    """Get direct download URL for instant download start.
    
    Returns direct URL if available, or None to indicate server download needed.
    This enables Y2Mate/SaveFrom-like instant download experience.
    """
    # Validate inputs
    if not url or not url.strip():
        raise HTTPException(status_code=400, detail="URL is required.")
    if not validate_video_url(url):
        raise HTTPException(status_code=400, detail="Invalid or unsupported video URL.")
    if media_format not in {"mp4", "mp3"}:
        raise HTTPException(status_code=400, detail="Format must be 'mp4' or 'mp3'.")
    
    try:
        result = await asyncio.to_thread(extract_direct_url, url, media_format, quality, audio_quality)
        
        if result:
            return JSONResponse(content={
                "success": True,
                "directUrl": result["url"],
                "filename": result["filename"],
                "filesize": result.get("filesize"),
            })
        else:
            # No direct URL, fallback to server download
            return JSONResponse(content={
                "success": False,
                "message": "Direct download not available, using server download."
            })
    except Exception as exc:
        # On error, fallback to server download
        return JSONResponse(content={
            "success": False,
            "message": str(exc)
        })


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
        from datetime import datetime
        
        # Get current timestamp
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
        # Create email message
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{name} <{SMTP_USERNAME}>"
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = f"New Contact Form Submission — VideoSnatcherz"
        msg["Reply-To"] = email

        # Email body with timestamp
        text_body = f"""
New Contact Form Submission — VideoSnatcherz

Submitted: {timestamp}

Contact Information:
-------------------
Name: {name}
Email: {email}

Subject:
--------
{subject}

Message:
--------
{message}

---
This message was sent via the VideoSnatcherz contact form.
Reply directly to {email} to respond.
"""

        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #22c55e, #14b8a6); padding: 20px; border-radius: 10px 10px 0 0;">
        <h2 style="color: white; margin: 0;">🎬 New Contact Form Submission</h2>
        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0 0; font-size: 14px;">VideoSnatcherz</p>
    </div>
    
    <div style="background: #f8fafc; padding: 20px; border-left: 4px solid #22c55e;">
        <p style="margin: 0; color: #64748b; font-size: 13px;">
            <strong>Submitted:</strong> {timestamp}
        </p>
    </div>
    
    <div style="padding: 20px; background: white;">
        <h3 style="color: #0f172a; margin-top: 0; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">
            Contact Information
        </h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; color: #64748b; width: 80px;"><strong>Name:</strong></td>
                <td style="padding: 8px 0; color: #0f172a;">{name}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #64748b;"><strong>Email:</strong></td>
                <td style="padding: 8px 0;">
                    <a href="mailto:{email}" style="color: #22c55e; text-decoration: none;">{email}</a>
                </td>
            </tr>
        </table>
        
        <h3 style="color: #0f172a; margin-top: 25px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">
            Subject
        </h3>
        <p style="color: #0f172a; margin: 10px 0;">{subject}</p>
        
        <h3 style="color: #0f172a; margin-top: 25px; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">
            Message
        </h3>
        <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; color: #0f172a; white-space: pre-wrap;">{message}</div>
    </div>
    
    <div style="background: #f8fafc; padding: 15px; border-radius: 0 0 10px 10px; text-align: center;">
        <p style="color: #64748b; font-size: 13px; margin: 0;">
            This message was sent via the VideoSnatcherz contact form.<br>
            <a href="mailto:{email}" style="color: #22c55e; text-decoration: none; font-weight: 600;">Click here to reply</a> or reply directly to this email.
        </p>
    </div>
</body>
</html>
"""

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Send email
        await asyncio.to_thread(_send_email, msg)

        return {
            "message": "Message sent successfully! We'll get back to you soon.",
            "success": True
        }

    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=503,
            detail="Email authentication failed. Please contact the administrator."
        )
    except smtplib.SMTPException as exc:
        raise HTTPException(
            status_code=503,
            detail="Failed to send email. Please try again later or contact us directly."
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later."
        ) from exc


def _send_email(msg: MIMEMultipart):
    """Send email using SMTP with SSL (blocking operation)."""
    # Use SMTP_SSL for port 465 (SSL/TLS)
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
