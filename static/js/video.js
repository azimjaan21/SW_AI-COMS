document.addEventListener("DOMContentLoaded", () => {
    const videoInput = document.getElementById("videoUpload");
    const dropZone = document.getElementById("dropZone");
    const videoPlayer = document.getElementById("videoPlayer"); // <img> for stream/preview
    const canvas = document.getElementById("overlayCanvas");
    const ctx = canvas.getContext("2d");
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");
    const checkboxes = document.querySelectorAll(".module-item input");

    let videoFile = null;
    let streamInterval = null;
    let streamActive = false;

    const PLACEHOLDER_SRC = "/static/images/cam.png"; 

    // ----------------- Drag & Drop -----------------
    dropZone.addEventListener("dragover", e => {
        e.preventDefault();
        dropZone.classList.add("dragover");
    });
    dropZone.addEventListener("dragleave", e => {
        dropZone.classList.remove("dragover");
    });
    dropZone.addEventListener("drop", e => {
        e.preventDefault();
        dropZone.classList.remove("dragover");
        if (e.dataTransfer.files.length) {
            videoFile = e.dataTransfer.files[0];
            uploadVideo(videoFile);
        }
    });

    // ----------------- File Input -----------------
    videoInput.addEventListener("change", () => {
        if (videoInput.files.length) {
            videoFile = videoInput.files[0];
            uploadVideo(videoFile);
        }
    });

    // ----------------- Upload Video -----------------
    function uploadVideo(file) {
        const formData = new FormData();
        formData.append("video", file);

        fetch("/api/inference/upload", {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === "ok") {
                console.log("📹 Video uploaded:", data.video_path);
                showPlaceholder(); // ✅ show placeholder after upload
            } else {
                alert("Upload failed: " + data.message);
            }
        })
        .catch(err => {
            console.error("Upload failed:", err);
        });
    }

    // ----------------- Show Placeholder -----------------
    function showPlaceholder() {
        videoPlayer.src = PLACEHOLDER_SRC;
        videoPlayer.style.display = "block";
        dropZone.style.display = "none";
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // adjust canvas to match image size
        videoPlayer.onload = () => {
            canvas.width = videoPlayer.width;
            canvas.height = videoPlayer.height;
        };
    }

    // ----------------- Start Stream -----------------
    startBtn.addEventListener("click", () => {
        if (!videoFile) {
            alert("Please upload a video first.");
            return;
        }

        const selectedModels = [];
        checkboxes.forEach(cb => { if (cb.checked) selectedModels.push(cb.value); });

        if (selectedModels.length === 0) {
            alert("Select at least one AI module.");
            return;
        }
        if (selectedModels.length > 2) {
            alert("Max 2 AI modules allowed.");
            return;
        }

        // Tell backend which models to run
        fetch("/api/inference/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ models: selectedModels })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === "ok") startStream();
            else alert("Backend failed: " + data.message);
        })
        .catch(err => console.error(err));
    });

    // ----------------- MJPEG Stream -----------------
    function startStream() {
        if (streamActive) return;
        streamActive = true;

        const img = new Image();
        canvas.width = videoPlayer.width;
        canvas.height = videoPlayer.height;

        function fetchFrame() {
            if (!streamActive) return;
            img.src = "/api/inference/stream?" + Date.now(); // cache buster
            img.onload = () => {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            };
        }

        streamInterval = setInterval(fetchFrame, 33); // ~30 FPS
    }

    // ----------------- Stop Stream -----------------
    stopBtn.addEventListener("click", () => {
        streamActive = false;
        if (streamInterval) clearInterval(streamInterval);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        showPlaceholder(); // ✅ show placeholder when stopped
        console.log("🛑 Stream stopped");
    });

    // ----------------- Max 2 Models Selection -----------------
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
