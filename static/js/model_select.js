document.addEventListener("DOMContentLoaded", () => {
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");
    const videoPlayer = document.getElementById("videoPlayer");
    const checkboxes = document.querySelectorAll(".module-item input");

    const videoInput = document.getElementById("videoUpload");
    const dropZone = document.getElementById("dropZone");

    const rtspInput = document.getElementById("rtspUrl");
    const addRtspBtn = document.getElementById("addRtspBtn");

    let videoFile = null;
    let rtspStream = null;
    const PLACEHOLDER_SRC = "/static/images/cam.png";

    // Show placeholder
    function showPlaceholder() {
        videoPlayer.src = PLACEHOLDER_SRC;
        videoPlayer.style.display = "block";
        dropZone.style.display = "none";
    }

    // ---------------- Upload Video ----------------
    function uploadVideo(file) {
        const formData = new FormData();
        formData.append("video", file);

        fetch("/api/inference/upload", { method: "POST", body: formData })
            .then(res => res.json())
            .then(data => {
                if (data.status === "ok") {
                    console.log("📹 Video uploaded:", data.video_path);
                    videoFile = file;
                    showPlaceholder();
                    rtspStream = null; // Clear any RTSP stream
                } else alert("Upload failed: " + data.message);
            })
            .catch(err => console.error(err));
    }

    videoInput.addEventListener("change", () => {
        if (videoInput.files.length) uploadVideo(videoInput.files[0]);
    });

    dropZone.addEventListener("drop", e => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length) uploadVideo(e.dataTransfer.files[0]);
    });

    dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("dragover"); });
    dropZone.addEventListener("dragleave", e => dropZone.classList.remove("dragover"));

    // ---------------- Add RTSP Stream ----------------
    addRtspBtn.addEventListener("click", () => {
        const url = rtspInput.value.trim();
        if (!url) return alert("Enter an RTSP URL first.");
        rtspStream = { id: "cam1", url }; // Can extend to multiple cameras later
        videoFile = null; // Clear uploaded video
        showPlaceholder(); // Show placeholder until stream starts
        console.log("📡 RTSP stream added:", rtspStream);
    });


// ---------------- Start Stream ----------------
startBtn.addEventListener("click", () => {
    const selectedModels = [];
    checkboxes.forEach(cb => { if (cb.checked) selectedModels.push(cb.value); });

    if (selectedModels.length === 0) return alert("Select at least one module");
    if (selectedModels.length > 2) return alert("Max 2 modules allowed");

    // Send models to backend
    fetch("/api/inference/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ models: selectedModels })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "ok") {
            if (videoFile) {
                // Uploaded video stream
                videoPlayer.src = "/api/inference/stream";
            } else if (rtspStream) {
                // RTSP stream — safely pass URL without double-encoding
                const safeUrl = rtspStream.url.includes("%") ? rtspStream.url : encodeURIComponent(rtspStream.url);
                videoPlayer.src = `/api/inference/stream_rtsp?id=${encodeURIComponent(rtspStream.id)}&url=${safeUrl}`;
            }
        } else {
            alert("Backend failed: " + data.message);
        }
    })
    .catch(err => console.error(err));
});


    // ---------------- Stop Stream ----------------
    stopBtn.addEventListener("click", () => {
        videoPlayer.src = "";
        showPlaceholder();
    });

    // ---------------- Max 2 Models UI ----------------
    checkboxes.forEach(cb => {
        cb.addEventListener("change", () => {
            const checkedCount = document.querySelectorAll(".module-item input:checked").length;
            checkboxes.forEach(box => {
                box.disabled = checkedCount >= 2 && !box.checked;
                box.parentElement.style.opacity = box.disabled ? "0.5" : "1";
            });
        });
    });
});
