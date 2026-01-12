document.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("startBtn");
  const stopBtn = document.getElementById("stopBtn");
  const videoPlayer = document.getElementById("videoPlayer");
  const checkboxes = document.querySelectorAll(".module-item input");
  const videoInput = document.getElementById("videoUpload");
  const dropZone = document.getElementById("dropZone");
  const rtspInput = document.getElementById("rtspUrl");
  const addRtspBtn = document.getElementById("addRtspBtn");

  // 🔥 Danger Zone buttons
  const dzDrawBtn = document.getElementById("dzDrawBtn");
  const dzSaveBtn = document.getElementById("dzSaveBtn");
  const dzDeleteBtn = document.getElementById("dzDeleteBtn");

  let videoFile = null;
  let rtspStream = null;
  let STREAM_RUNNING = false;
  let DANGER_ZONE_SELECTED = false;

  const PLACEHOLDER_SRC = "/static/images/cam.png";

  // ---------- Helpers ----------
  const showPlaceholder = () => {
    videoPlayer.src = PLACEHOLDER_SRC;
    videoPlayer.style.display = "block";
    dropZone.style.display = "none";
  };

  const updateDangerZoneUI = () => {
    const enabled = STREAM_RUNNING && DANGER_ZONE_SELECTED;

    dzDrawBtn.disabled = !enabled;
    dzSaveBtn.disabled = !enabled;
    dzDeleteBtn.disabled = !enabled;

    // expose to danger_zone.js
    window.DANGER_ZONE_ACTIVE = enabled;
  };

  const uploadVideo = (file) => {
    const formData = new FormData();
    formData.append("video", file);

    fetch("/api/inference/upload", { method: "POST", body: formData })
      .then(res => res.json())
      .then(data => {
        if (data.status === "ok") {
          console.log("📹 Video uploaded:", data.video_path);
          videoFile = file;
          rtspStream = null;
          showPlaceholder();
        } else {
          alert("Upload failed: " + data.message);
        }
      })
      .catch(err => console.error(err));
  };

  const updateCheckboxesUI = () => {
    const checkedCount = document.querySelectorAll(".module-item input:checked").length;
    checkboxes.forEach(cb => {
      cb.disabled = checkedCount >= 2 && !cb.checked;
      cb.parentElement.style.opacity = cb.disabled ? "0.5" : "1";
    });
  };

  // ---------- Event Listeners ----------
  // Video upload
  videoInput.addEventListener("change", () => {
    if (videoInput.files.length) uploadVideo(videoInput.files[0]);
  });

  dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length) uploadVideo(e.dataTransfer.files[0]);
  });

  dropZone.addEventListener("dragover", e => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));

  // RTSP stream
  addRtspBtn.addEventListener("click", () => {
    const url = rtspInput.value.trim();
    if (!url) return alert("Enter an RTSP URL first.");
    rtspStream = { id: "cam1", url };
    videoFile = null;
    showPlaceholder();
    console.log("📡 RTSP stream added:", rtspStream);
  });

  // Detect danger zone checkbox
  document.querySelector('input[value="danger_zone"]').addEventListener("change", (e) => {
    DANGER_ZONE_SELECTED = e.target.checked;
    updateDangerZoneUI();
  });

  // Start stream
  startBtn.addEventListener("click", () => {
    const selectedModels = Array.from(checkboxes)
      .filter(cb => cb.checked)
      .map(cb => cb.value);

    if (!selectedModels.length) return alert("Select at least one module");
    if (selectedModels.length > 2) return alert("Max 2 modules allowed");

    fetch("/api/inference/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ models: selectedModels })
    })
      .then(res => res.json())
      .then(data => {
        if (data.status === "ok") {
          STREAM_RUNNING = true;
          updateDangerZoneUI();

          if (videoFile) {
            videoPlayer.src = "/api/inference/stream";
          } else if (rtspStream) {
            const safeUrl = rtspStream.url.includes("%")
              ? rtspStream.url
              : encodeURIComponent(rtspStream.url);
            videoPlayer.src = `/api/inference/stream_rtsp?id=${encodeURIComponent(rtspStream.id)}&url=${safeUrl}`;
          }
        } else {
          alert("Backend failed: " + data.message);
        }
      })
      .catch(err => console.error(err));
  });

  // Stop stream
  stopBtn.addEventListener("click", () => {
    videoPlayer.src = "";
    STREAM_RUNNING = false;
    updateDangerZoneUI();
    showPlaceholder();
  });

  // Max 2 modules UI
  checkboxes.forEach(cb => cb.addEventListener("change", updateCheckboxesUI));
});
