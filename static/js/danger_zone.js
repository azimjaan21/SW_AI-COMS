/* ================= Elements ================= */
const canvas = document.getElementById("overlay");
const ctx = canvas.getContext("2d");
const videoEl = document.getElementById("videoPlayer");

/* Buttons */
const drawBtn = document.getElementById("dzDrawBtn");
const saveBtn = document.getElementById("dzSaveBtn");
const deleteBtn = document.getElementById("dzDeleteBtn");

/* ================= State ================= */
let zones = [];
let current = [];
let drawing = false;

let dangerModeEnabled = false;
let streamRunning = false;

let alertActive = false;
let flash = false;

/* ================= Canvas Resize ================= */
function resizeCanvas() {
    if (!videoEl || !videoEl.clientWidth) return;
    canvas.width = videoEl.clientWidth;
    canvas.height = videoEl.clientHeight;
}
window.addEventListener("resize", resizeCanvas);
videoEl.onload = resizeCanvas;

/* ================= Control Logic ================= */
function controlsEnabled() {
    return dangerModeEnabled && streamRunning;
}

function updateButtons() {
    const enabled = controlsEnabled();
    drawBtn.disabled = !enabled;
    saveBtn.disabled = !enabled;
    deleteBtn.disabled = !enabled;
}

/* ================= Canvas Click ================= */
canvas.addEventListener("click", (e) => {
    if (!drawing || !controlsEnabled()) return;

    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / canvas.width;
    const y = (e.clientY - rect.top) / canvas.height;

    current.push([x, y]);
    draw();
});

/* ================= Buttons ================= */
drawBtn.onclick = () => {
    if (!controlsEnabled()) return;
    drawing = true;
    current = [];
};

saveBtn.onclick = async () => {
    if (!controlsEnabled()) return;
    if (current.length < 3) {
        alert("Polygon needs at least 3 points");
        return;
    }

    await fetch("/api/zones/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            camera_id: CAMERA_ID,
            points: current
        })
    });

    drawing = false;
    current = [];
    loadZones();
};

deleteBtn.onclick = async () => {
    if (!controlsEnabled()) return;

    await fetch(`/api/zones/delete_all/${CAMERA_ID}/`, {
        method: "DELETE"
    });

    zones = [];
    draw();
};

/* ================= Backend ================= */
async function loadZones() {
    const res = await fetch(`/api/zones/?camera_id=${CAMERA_ID}`);
    zones = await res.json();
    draw();
}

/* ================= Flash Alert ================= */
setInterval(() => {
    if (alertActive) flash = !flash;
    draw();
}, 400);

/* ================= Drawing ================= */
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    zones.forEach(z => drawPoly(z.points));
    if (current.length) drawPoly(current, true);
}

function drawPoly(points, dashed = false) {
    ctx.beginPath();
    points.forEach(([x, y], i) => {
        const px = x * canvas.width;
        const py = y * canvas.height;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
    });
    ctx.closePath();

    ctx.strokeStyle = "red";
    ctx.lineWidth = alertActive ? 4 : 2;
    ctx.setLineDash(dashed ? [8, 5] : []);

    ctx.fillStyle = `rgba(255,0,0,${alertActive && flash ? 0.6 : 0.25})`;

    ctx.stroke();
    ctx.fill();
}

/* ================= External Hooks ================= */
window.enableDangerZoneMode = (active) => {
    dangerModeEnabled = active;
    updateButtons();
};

window.setStreamRunning = (active) => {
    streamRunning = active;
    updateButtons();
};

window.setDangerAlert = (active) => {
    alertActive = active;
};

/* ================= Init ================= */
updateButtons();
loadZones();
