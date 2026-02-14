const form = document.getElementById("download-form");
const statusEl = document.getElementById("status");
const submitBtn = document.getElementById("submit-btn");
const btnText = document.getElementById("btn-text");
const btnSpinner = document.getElementById("btn-spinner");
const errorBox = document.getElementById("error-box");
const urlInput = form.querySelector('input[name="url"]');
const formatSelect = document.getElementById("format-select");
const videoQuality = document.getElementById("video-quality");
const audioQuality = document.getElementById("audio-quality");
const qualityLabel = document.getElementById("quality-label");
const qualityHint = document.getElementById("quality-hint");

const progressContainer = document.getElementById("progress-container");
const progressFill = document.getElementById("progress-fill");
const progressText = document.getElementById("progress-text");

const thumbImg = document.getElementById("thumb-img");
const thumbPlaceholder = document.getElementById("thumb-placeholder");
const metaTitle = document.getElementById("meta-title");
const metaSub = document.getElementById("meta-sub");

let metaDebounce;
let progressEventSource = null;

// Progress bar control functions
const showProgress = () => {
  progressContainer.classList.remove("hidden");
  progressFill.style.width = "0%";
  progressText.textContent = "0%";
};

const updateProgress = (percentage) => {
  progressFill.style.width = percentage + "%";
  progressText.textContent = percentage + "%";
};

const hideProgress = () => {
  progressContainer.classList.add("hidden");
  progressFill.style.width = "0%";
  progressText.textContent = "0%";
};

// Progress tracking function
const trackProgress = (downloadId, onProgress) => {
  // Close any existing connection
  if (progressEventSource) {
    progressEventSource.close();
  }
  
  progressEventSource = new EventSource(`/api/progress/${downloadId}`);
  
  progressEventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      
      // Update progress bar
      if (data.percentage !== undefined) {
        updateProgress(data.percentage);
      }
      
      // Call custom progress handler
      onProgress(data);
      
      // Close connection when complete or timeout
      if (data.status === 'complete' || data.status === 'timeout') {
        progressEventSource.close();
        progressEventSource = null;
      }
    } catch (err) {
      console.error('Progress parse error:', err);
    }
  };
  
  progressEventSource.onerror = () => {
    progressEventSource.close();
    progressEventSource = null;
  };
  
  return progressEventSource;
};

// URL validation function
const isValidVideoURL = (url) => {
  if (!url || url.trim() === "") return false;
  
  // Check if it's a valid URL format
  try {
    const urlObj = new URL(url);
    // Check for common video platforms
    const validDomains = [
      'youtube.com', 'youtu.be', 'm.youtube.com', 'www.youtube.com',
      'vimeo.com', 'dailymotion.com', 'twitch.tv'
    ];
    return validDomains.some(domain => urlObj.hostname.includes(domain));
  } catch {
    return false;
  }
};

const setInputError = (hasError) => {
  if (hasError) {
    urlInput.classList.add("input-error");
  } else {
    urlInput.classList.remove("input-error");
  }
};

const setStatus = (text, isError = false) => {
  if (!text) {
    statusEl.classList.add("hidden");
    statusEl.textContent = "";
    return;
  }
  statusEl.textContent = text;
  statusEl.classList.toggle("error", isError);
  statusEl.classList.remove("hidden");
};

const showErrorBox = (message) => {
  if (!message) {
    errorBox.classList.add("hidden");
    errorBox.textContent = "";
    return;
  }
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
};

const setButtonLoading = (isLoading) => {
  submitBtn.disabled = isLoading;
  btnSpinner.classList.toggle("hidden", !isLoading);
  btnText.textContent = isLoading ? "Processing..." : "Download";
};

const resetPreview = () => {
  const preview = document.getElementById("preview");
  preview.setAttribute("data-state", "empty");
  thumbImg.style.display = "none";
  thumbImg.src = "";
  thumbPlaceholder.textContent = "Paste a link to preview";
  thumbPlaceholder.style.display = "grid";
  metaTitle.textContent = "No video loaded";
  metaSub.textContent = "Duration will appear here";
};

const formatDuration = (seconds) => {
  if (!seconds && seconds !== 0) return "Duration unavailable";
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60)
    .toString()
    .padStart(2, "0");
  const hours = Math.floor(mins / 60);
  if (hours > 0) {
    const remMins = (mins % 60).toString().padStart(2, "0");
    return `${hours}:${remMins}:${secs}`;
  }
  return `${mins}:${secs}`;
};

const fetchMetadata = async (url) => {
  const preview = document.getElementById("preview");
  
  if (!url) {
    resetPreview();
    setInputError(false);
    setStatus("");
    return;
  }
  
  // Validate URL before making API call
  if (!isValidVideoURL(url)) {
    resetPreview();
    preview.setAttribute("data-state", "error");
    setInputError(true);
    showErrorBox("⚠️ Please enter a valid video link (YouTube, Vimeo, etc.)");
    setStatus("");
    return;
  }
  
  try {
    // Show loading state
    preview.setAttribute("data-state", "loading");
    setStatus("🔍 Fetching video info...");
    showErrorBox("");
    setInputError(false);
    
    const res = await fetch(`/api/metadata?url=${encodeURIComponent(url)}`);
    if (!res.ok) {
      const text = await res.text();
      let detail = "Unable to fetch video information. Please check the URL and try again.";
      try {
        const parsed = JSON.parse(text);
        if (parsed.detail) {
          // Clean up technical error messages
          detail = parsed.detail.includes("ERROR:") 
            ? "Video not available or URL is invalid."
            : parsed.detail;
        }
      } catch (_) {
        /* ignore parse failure */
      }
      throw new Error(detail);
    }
    
    const data = await res.json();
    
    // Update metadata
    metaTitle.textContent = data.title || "Untitled video";
    metaSub.textContent = `${data.uploader ? data.uploader + " • " : ""}${formatDuration(data.duration)}`;

    // Handle thumbnail
    if (data.thumbnail) {
      thumbImg.onload = () => {
        thumbPlaceholder.style.display = "none";
        thumbImg.style.display = "block";
        preview.setAttribute("data-state", "loaded");
      };
      thumbImg.onerror = () => {
        thumbImg.style.display = "none";
        thumbPlaceholder.style.display = "grid";
        thumbPlaceholder.textContent = "Thumbnail unavailable";
        preview.setAttribute("data-state", "loaded");
      };
      thumbImg.src = data.thumbnail;
    } else {
      thumbImg.style.display = "none";
      thumbPlaceholder.style.display = "grid";
      thumbPlaceholder.textContent = "Thumbnail unavailable";
      preview.setAttribute("data-state", "loaded");
    }
    
    showErrorBox("");
    setStatus("");
  } catch (err) {
    resetPreview();
    preview.setAttribute("data-state", "error");
    setInputError(true);
    showErrorBox("⚠️ " + (err.message || "Could not fetch video info."));
    setStatus("");
  }
};

const toggleQualityOptions = () => {
  const format = formatSelect.value;
  const isAudio = (format === "mp3" || format === "m4a");
  const isMP3 = format === "mp3";
  const isM4A = format === "m4a";
  
  // Show video quality for MP4, audio quality for MP3, hide for M4A
  videoQuality.classList.toggle("hidden", isAudio);
  audioQuality.classList.toggle("hidden", !isMP3);
  
  // Update labels
  if (isMP3) {
    qualityLabel.textContent = "Audio quality";
    qualityHint.textContent = "Bitrate";
  } else if (isM4A) {
    qualityLabel.textContent = "Audio quality";
    qualityHint.textContent = "Best available";
  } else {
    qualityLabel.textContent = "Max quality";
    qualityHint.textContent = "Cap resolution";
  }
  
  // Set correct form field names
  if (isMP3) {
    videoQuality.removeAttribute("name");
    audioQuality.setAttribute("name", "audio_quality");
  } else {
    audioQuality.removeAttribute("name");
    if (!isM4A) {
      videoQuality.setAttribute("name", "quality");
    } else {
      videoQuality.removeAttribute("name");
    }
  }
};

formatSelect.addEventListener("change", toggleQualityOptions);

urlInput.addEventListener("input", () => {
  clearTimeout(metaDebounce);
  metaDebounce = setTimeout(() => fetchMetadata(urlInput.value.trim()), 550);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  
  const url = urlInput.value.trim();
  
  // Validate URL before submitting
  if (!isValidVideoURL(url)) {
    setInputError(true);
    showErrorBox("⚠️ Please enter a valid video link before downloading.");
    setStatus("");
    return;
  }
  
  const format = formatSelect.value;
  const isAudio = (format === "mp3" || format === "m4a");
  const isMP3 = format === "mp3";
  const isM4A = format === "m4a";
  
  setButtonLoading(true);
  showErrorBox("");
  setInputError(false);
  
  if (isMP3) {
    setStatus("🎵 Extracting audio...");
  } else if (isM4A) {
    setStatus("⚡ Starting audio download...");
  } else {
    setStatus("⚡ Starting download...");
  }

  const data = new FormData(form);
  
  // Clean up unused quality parameters
  if (isMP3) {
    data.delete("quality");
    if (!data.get("audio_quality")) {
      data.delete("audio_quality");
    }
  } else if (isM4A) {
    // M4A doesn't use quality parameters
    data.delete("quality");
    data.delete("audio_quality");
  } else {
    data.delete("audio_quality");
    if (!data.get("quality")) {
      data.delete("quality");
    }
  }

  try {
    // For audio downloads, try streaming first (for M4A instant download)
    if (isAudio) {
      let useStreaming = true;
      
      // MP3 conversions will fall back to regular download automatically
      if (isMP3) {
        setStatus("🎵 Preparing MP3...");
        useStreaming = false;  // Skip streaming for MP3
      } else {
        setStatus("⚡ Streaming audio download...");
      }
      
      if (useStreaming) {
        try {
          const streamRes = await fetch("/api/stream-audio", {
            method: "POST",
            body: data,
          });
          
          if (streamRes.ok) {
            setStatus("📥 Receiving audio...");
            const blob = await streamRes.blob();
            const disposition = streamRes.headers.get("Content-Disposition") || "";
            const nameMatch = disposition.match(/filename="?([^";]+)"?/i);
            const filename = nameMatch ? nameMatch[1] : `audio.${isMP3 ? 'mp3' : 'm4a'}`;

            const blobUrl = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(blobUrl);

            setStatus("");
            showErrorBox("");
            setButtonLoading(false);
            return;  // Success!
          }
        } catch (streamErr) {
          console.log("Streaming failed, falling back to regular download:", streamErr);
          // Fall through to regular download
        }
      }
      
      // Fallback: Use regular download endpoint for audio
      setStatus(isMP3 ? "🎵 Converting to MP3..." : "⏳ Preparing audio...");
      
      // Generate download ID and start progress tracking
      const downloadId = 'dl_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      data.append('download_id', downloadId);
      
      // Show progress bar and start progress tracking
      showProgress();
      trackProgress(downloadId, (progressData) => {
        if (progressData.percentage !== undefined) {
          const status = progressData.status === 'processing' ? '⚙️ Processing' : '⏳ Downloading';
          setStatus(`${status}...`);
        }
      });
      
      const res = await fetch("/api/download", {
        method: "POST",
        body: data,
      });
      
      if (!res.ok) {
        hideProgress();
        if (progressEventSource) {
          progressEventSource.close();
          progressEventSource = null;
        }
        const text = await res.text();
        let detail = "Audio download failed. Please try again.";
        try {
          const parsed = JSON.parse(text);
          if (parsed.detail) {
            if (parsed.detail.includes("FFmpeg")) {
              detail = "FFmpeg is required for MP3 conversion. Please check the setup guide.";
            } else {
              detail = parsed.detail;
            }
          }
        } catch (_) {
          /* ignore parse failure */
        }
        throw new Error(detail);
      }
      
      // Complete - get the file
      updateProgress(100);
      setStatus("✓ Download complete!");
      
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") || "";
      const nameMatch = disposition.match(/filename="?([^";]+)"?/i);
      const filename = nameMatch ? nameMatch[1] : `audio.${isMP3 ? 'mp3' : 'm4a'}`;

      // Trigger download
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      
      // Cleanup
      setTimeout(() => {
        window.URL.revokeObjectURL(blobUrl);
        hideProgress();
        setStatus("");
        showErrorBox("");
        setButtonLoading(false);
      }, 500);
      
      // Close progress tracking
      if (progressEventSource) {
        progressEventSource.close();
        progressEventSource = null;
      }
      
      return;  // Audio download complete
    }
    
    // For video downloads, try direct URL first
    setStatus("⚡ Getting download link...");
    
    const directUrlRes = await fetch("/api/get-download-url", {
      method: "POST",
      body: data,
    });
    
    if (directUrlRes.ok) {
      const directUrlData = await directUrlRes.json();
      
      if (directUrlData.success && directUrlData.directUrl) {
        // SUCCESS: Direct URL available - download instantly!
        setStatus("✓ Download starting now!");
        
        // Create hidden link and trigger download
        const a = document.createElement("a");
        a.href = directUrlData.directUrl;
        a.download = directUrlData.filename || "download";
        a.style.display = "none";
        document.body.appendChild(a);
        a.click();
        
        // Cleanup after a short delay
        setTimeout(() => {
          document.body.removeChild(a);
          setStatus("");
          showErrorBox("");
          setButtonLoading(false);
        }, 1000);
        
        return; // Exit - download started!
      }
    }
    
    // Step 2: Direct URL not available, fallback to server download
    setStatus("⏳ Preparing file on server...");
    
    // Generate download ID and start progress tracking
    const downloadId = 'dl_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    data.append('download_id', downloadId);
    
    // Show progress bar and start progress tracking
    showProgress();
    trackProgress(downloadId, (progressData) => {
      if (progressData.percentage !== undefined) {
        const status = progressData.status === 'processing' ? '⚙️ Processing' : '📥 Downloading';
        setStatus(`${status}...`);
      }
    });
    
    const res = await fetch("/api/download", {
      method: "POST",
      body: data,
    });

    if (!res.ok) {
      hideProgress();
      if (progressEventSource) {
        progressEventSource.close();
        progressEventSource = null;
      }
      const text = await res.text();
      let detail = "Download failed. Please try again or choose a different quality.";
      try {
        const parsed = JSON.parse(text);
        if (parsed.detail) {
          // Clean up technical error messages
          if (parsed.detail.includes("FFmpeg")) {
            detail = "FFmpeg is required for this download. Please check the setup guide.";
          } else if (parsed.detail.includes("ERROR:")) {
            detail = "Video unavailable or restricted. Try a different video.";
          } else {
            detail = parsed.detail;
          }
        }
      } catch (_) {
        /* ignore parse failure */
      }
      throw new Error(detail);
    }

    // Complete - get the file
    updateProgress(100);
    setStatus("✓ Download complete!");
    
    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const nameMatch = disposition.match(/filename="?([^";]+)"?/i);
    const filename = nameMatch ? nameMatch[1] : "download";

    // Trigger download
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    
    // Cleanup
    setTimeout(() => {
      window.URL.revokeObjectURL(blobUrl);
      hideProgress();
      setStatus("");
      showErrorBox("");
    }, 500);
    
    // Close progress tracking
    if (progressEventSource) {
      progressEventSource.close();
      progressEventSource = null;
    }
  } catch (err) {
    console.error(err);
    hideProgress();
    if (progressEventSource) {
      progressEventSource.close();
      progressEventSource = null;
    }
    setInputError(true);
    showErrorBox("⚠️ " + (err.message || "Something went wrong."));
    setStatus("");
  } finally {
    setButtonLoading(false);
  }
});

// Initial state
toggleQualityOptions();
resetPreview();
showErrorBox("");

// Check for pending URL from homepage
const pendingUrl = sessionStorage.getItem('pendingDownloadUrl');
if (pendingUrl) {
  urlInput.value = pendingUrl;
  sessionStorage.removeItem('pendingDownloadUrl');
  // Trigger metadata fetch
  fetchMetadata(pendingUrl);
  // Focus on format selector
  setTimeout(() => formatSelect.focus(), 100);
}

// Cleanup SSE connection when page unloads
window.addEventListener('beforeunload', () => {
  if (progressEventSource) {
    progressEventSource.close();
    progressEventSource = null;
  }
});
