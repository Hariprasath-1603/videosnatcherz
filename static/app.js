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

const thumbImg = document.getElementById("thumb-img");
const thumbPlaceholder = document.getElementById("thumb-placeholder");
const metaTitle = document.getElementById("meta-title");
const metaSub = document.getElementById("meta-sub");

let metaDebounce;

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
  statusEl.textContent = text;
  statusEl.classList.toggle("error", isError);
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
  btnText.textContent = isLoading ? "Working..." : "Download";
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
    return;
  }
  
  // Validate URL before making API call
  if (!isValidVideoURL(url)) {
    resetPreview();
    preview.setAttribute("data-state", "error");
    setInputError(true);
    showErrorBox("⚠️ Please enter a valid video link (YouTube, Vimeo, etc.)");
    setStatus("Invalid URL", true);
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
    setStatus("✓ Ready to download");
  } catch (err) {
    resetPreview();
    preview.setAttribute("data-state", "error");
    setInputError(true);
    showErrorBox("⚠️ " + (err.message || "Could not fetch video info."));
    setStatus("Metadata error", true);
  }
};

const toggleQualityOptions = () => {
  const isMP3 = formatSelect.value === "mp3";
  videoQuality.classList.toggle("hidden", isMP3);
  audioQuality.classList.toggle("hidden", !isMP3);
  qualityLabel.textContent = isMP3 ? "Audio quality" : "Max quality";
  qualityHint.textContent = isMP3 ? "Bitrate" : "Cap resolution";
  
  if (isMP3) {
    videoQuality.removeAttribute("name");
    audioQuality.setAttribute("name", "audio_quality");
  } else {
    audioQuality.removeAttribute("name");
    videoQuality.setAttribute("name", "quality");
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
    setStatus("Invalid URL", true);
    return;
  }
  
  setButtonLoading(true);
  showErrorBox("");
  setInputError(false);
  setStatus("Preparing download...");

  const data = new FormData(form);
  const isMP3 = formatSelect.value === "mp3";
  
  // Clean up unused quality parameters
  if (isMP3) {
    data.delete("quality");
    if (!data.get("audio_quality")) {
      data.delete("audio_quality");
    }
  } else {
    data.delete("audio_quality");
    if (!data.get("quality")) {
      data.delete("quality");
    }
  }

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      body: data,
    });

    if (!res.ok) {
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

    const blob = await res.blob();
    const disposition = res.headers.get("Content-Disposition") || "";
    const nameMatch = disposition.match(/filename="?([^";]+)"?/i);
    const filename = nameMatch ? nameMatch[1] : "download";

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    setStatus("Download started. If nothing happened, check your browser's download bar.");
  } catch (err) {
    console.error(err);
    setInputError(true);
    showErrorBox("⚠️ " + (err.message || "Something went wrong."));
    setStatus("Download failed", true);
  } finally {
    setButtonLoading(false);
  }
});

// Initial state
toggleQualityOptions();
resetPreview();
showErrorBox("");
