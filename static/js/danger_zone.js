/* ================= Elements ================= */
const canvas = document.getElementById("overlay");
const ctx = canvas.getContext("2d");

const videoEl = document.getElementById("videoPlayer");

/* Buttons (MATCH HTML IDs) */
const drawBtn = document.getElementById("dzDrawBtn");
const saveBtn = document.getElementById("dzSaveBtn");
const deleteBtn = document.getElementById("dzDeleteBtn");

/* ================= State ================= */
let zones = [];
let current = [];
let drawing = false;

let alertActive = false;
let flash = false;

/* Control flags */
let dangerModeEnabled = false;
let streamRunning = false;

/* ================= Canvas Resize ================= */
function resizeCanvas() {
    if (!videoEl) return;

    canvas.width = videoEl.clientWidth;
    canvas.height = videoEl.clientHeight;
}
window.addEventListener("resize", resizeCanvas);
setTimeout(resizeCanvas, 500);

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
    current.push([
        (e.clientX - rect.left) / canvas.width,
        (e.clientY - rect.top) / canvas.height
    ]);
    draw();
});

/* ================= Buttons ================= */
drawBtn.onclick = () => {
    if (!controlsEnabled()) return;
    drawing = true;
    current = [];
};

saveBtn.onclick = saveZone;
deleteBtn.onclick = deleteAll;

/* ================= Backend Calls ================= */
async function saveZone() {
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
}

async function deleteAll() {
    if (!controlsEnabled()) return;

    await fetch(`/api/zones/delete_all/${CAMERA_ID}/`, {
        method: "DELETE"
    });

    zones = [];
    draw();
}

async function loadZones() {
    const res = await fetch(`/api/zones/?camera_id=${CAMERA_ID}`);
    zones = await res.json();
    draw();
}

/* ================= Flash Effect ================= */
setInterval(() => {
    if (alertActive) flash = !flash;
    draw();
}, 400);

/* ================= Drawing ================= */
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    zones.forEach(z => drawPoly(z.points));
    if (current.length > 0) drawPoly(current, true);
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

/* ================= Hooks from UI / Backend ================= */
window.setDangerAlert = (active) => {
    alertActive = active;
};

window.enableDangerZoneMode = (active) => {
    dangerModeEnabled = active;
    updateButtons();
};

window.setStreamRunning = (active) => {
    streamRunning = active;
    updateButtons();
};

/* ================= Init ================= */
updateButtons();
loadZones();
