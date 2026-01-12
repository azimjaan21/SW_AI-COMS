import os
import cv2
from flask import Blueprint, Response, request, jsonify
from ultralytics import YOLO
import torch
import time
import numpy as np

inference_bp = Blueprint("inference", __name__)

# ---------------- Device & Models ----------------
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
print(f" Using device: {DEVICE}")

MODEL_PATHS = {
    "ppe": "models/ppe.pt",
    "fire": "models/fire.pt",
    "forklift": "models/forklift.pt",
    "danger_zone": "models/yolo11s-pose.pt",
    "fall": "models/yolo11s-pose.pt",
}

MODELS = {}
for name, path in MODEL_PATHS.items():
    if os.path.exists(path):
        MODELS[name] = YOLO(path).to(DEVICE)
        print(f"✅ Loaded {name} model on {DEVICE}")
    else:
        print(f"⚠️ Model not found: {path}")

# ---------------- Globals ----------------
CURRENT_MODELS = []
VIDEO_PATH = None
fall_states = {}  # store fall info per track_id

# ---------------- Custom Colors ----------------
COLORS = {
    "helmet": (0, 255, 0),       # Green
    "vest": (0, 255, 0),         # Green
    "head": (0, 0, 255),         # Red
    "forklift": (0, 255, 255),   # Yellow
    "fall_keypoints": (0, 255, 255),   # Yellow dots
    "fall_skeleton": (255, 200, 100),  # Light blue lines
    "fall_alert_text": (0, 0, 255),     # Red alert text
    "fire": (0, 0, 255),          # Red fire
    "smoke": (128, 128, 128)      # Gray smoke
}

# ---------------- Fall Utils ----------------
def draw_keypoints(frame, keypoints, confidence_threshold=0.5):
    if len(keypoints) == 0:
        return
    skeleton = [[15, 13], [13, 11], [16, 14], [14, 12], [11, 12], 
                [5, 11], [6, 12], [5, 6], [5, 7], [6, 8], [7, 9], 
                [8, 10], [1, 2], [0, 1], [0, 2], [1, 3], [2, 4],
                [3, 5], [4, 6]]
    for p1, p2 in skeleton:
        if (p1 < len(keypoints) and p2 < len(keypoints) and
            keypoints[p1][2] > confidence_threshold and 
            keypoints[p2][2] > confidence_threshold):
            cv2.line(frame,
                     (int(keypoints[p1][0]), int(keypoints[p1][1])),
                     (int(keypoints[p2][0]), int(keypoints[p2][1])),
                     COLORS["fall_skeleton"], 2)
    for kp in keypoints:
        x, y, conf = kp
        if conf > confidence_threshold:
            cv2.circle(frame, (int(x), int(y)), 4, COLORS["fall_keypoints"], -1)

def calculate_movement_speed(current_pos, history):
    if len(history) < 2:
        return 0, 0
    history = np.array(history)
    displacements = np.diff(history, axis=0)
    v_displacements = np.abs(displacements[:, 1])
    h_displacements = np.abs(displacements[:, 0])
    return np.mean(v_displacements), np.mean(h_displacements)

def detect_fall(keypoints, track_id, frame_height, fall_duration_threshold=3.0):
    if len(keypoints) < 17:
        return False

    # Extract keypoints
    nose = keypoints[0]
    left_shoulder = keypoints[5]
    right_shoulder = keypoints[6]
    left_hip = keypoints[11]
    right_hip = keypoints[12]
    left_ankle = keypoints[15]
    right_ankle = keypoints[16]

    key_points = [nose, left_shoulder, right_shoulder, left_hip, right_hip, left_ankle, right_ankle]
    if any(kp[2] < 0.5 for kp in key_points):
        return False

    shoulder_center = [(left_shoulder[0] + right_shoulder[0])/2,
                       (left_shoulder[1] + right_shoulder[1])/2]
    hip_mid = [(left_hip[0] + right_hip[0])/2,
               (left_hip[1] + right_hip[1])/2]
    ankle_center = [(left_ankle[0] + right_ankle[0])/2,
                    (left_ankle[1] + right_ankle[1])/2]
    center = hip_mid

    spine_angle = abs(np.degrees(np.arctan2(
        shoulder_center[1] - hip_mid[1],
        shoulder_center[0] - hip_mid[0]
    )))

    if track_id not in fall_states:
        fall_states[track_id] = {
            'falling_frames': 0,
            'is_fallen': False,
            'position_history': [],
            'last_update_time': time.time(),
            'normal_height': None,
            'last_spine_angle': spine_angle,
            'time_still': 0,
            'confirmation_frames': 0,
            'fall_start_time': None
        }

    angle_change = abs(spine_angle - fall_states[track_id].get('last_spine_angle', spine_angle))
    fall_states[track_id]['last_spine_angle'] = spine_angle

    current_time = time.time()
    if current_time - fall_states[track_id]['last_update_time'] > 0.01:
        fall_states[track_id]['position_history'].append(center)
        fall_states[track_id]['last_update_time'] = current_time
        if len(fall_states[track_id]['position_history']) > 10:
            fall_states[track_id]['position_history'].pop(0)

    v_speed, h_speed = calculate_movement_speed(center, fall_states[track_id]['position_history'])
    sudden_angle_change = angle_change > 65
    shoulder_hip_ratio = abs(shoulder_center[1] - hip_mid[1]) / frame_height
    is_unusual_pose = shoulder_hip_ratio < 0.2
    total_speed = np.sqrt(v_speed**2 + h_speed**2)
    is_rapid_movement = total_speed > 10

    current_height = abs(shoulder_center[1] - ankle_center[1])
    if fall_states[track_id]['normal_height'] is None:
        fall_states[track_id]['normal_height'] = current_height
    height_ratio = current_height / fall_states[track_id]['normal_height'] if fall_states[track_id]['normal_height'] else 1

    if total_speed < 0.5:
        fall_states[track_id]['time_still'] += 1
    else:
        fall_states[track_id]['time_still'] = 0

    is_fall_candidate = (
        (sudden_angle_change and is_rapid_movement) or
        (is_unusual_pose and height_ratio < 0.85)
    )

    if fall_states[track_id]['time_still'] > 60:
        is_fall_candidate = True

    if is_fall_candidate:
        fall_states[track_id]['falling_frames'] += 2
        fall_states[track_id]['confirmation_frames'] += 1
        if fall_states[track_id]['fall_start_time'] is None:
            fall_states[track_id]['fall_start_time'] = current_time
    else:
        fall_states[track_id]['falling_frames'] = max(0, fall_states[track_id]['falling_frames'] - 1)
        fall_states[track_id]['confirmation_frames'] = 0
        fall_states[track_id]['fall_start_time'] = None

    if fall_states[track_id]['confirmation_frames'] > 5:
        if fall_states[track_id]['fall_start_time'] and (current_time - fall_states[track_id]['fall_start_time'] >= fall_duration_threshold):
            fall_states[track_id]['is_fallen'] = True

    return fall_states[track_id]['is_fallen']

# ---------------- Start Analysis ----------------
@inference_bp.route("/start", methods=["POST"])
def start_analysis():
    global CURRENT_MODELS
    selected_models = request.json.get("models", [])

    if not selected_models:
        return jsonify({"status": "error", "message": "Select at least one model"}), 400
    if len(selected_models) > 2:
        return jsonify({"status": "error", "message": "Maximum 2 models allowed"}), 400

    valid_models = [m for m in selected_models if m in MODELS]
    if not valid_models:
        return jsonify({"status": "error", "message": "No valid models selected"}), 400

    CURRENT_MODELS = valid_models
    print(f"🔥 Analysis started with models: {CURRENT_MODELS}")

    if "fall" not in CURRENT_MODELS:
        fall_states.clear()

    return jsonify({"status": "ok", "models": CURRENT_MODELS})

# ---------------- Custom Drawing Functions ----------------
def draw_ppe_forklift_fire_smoke(frame, results, model_name):
    for idx, box in enumerate(results[0].boxes.data):
        cls_id = int(results[0].boxes.cls[idx])
        cls_name = results[0].names[cls_id]
        x1, y1, x2, y2 = box[:4].cpu().numpy().astype(int)

        color = (255, 255, 255)  # default
        if model_name == "ppe":
            if cls_name in ["helmet", "vest"]:
                color = COLORS["helmet"]
            elif cls_name == "head":
                color = COLORS["head"]
        elif model_name == "forklift":
            color = COLORS["forklift"]
        elif model_name == "fire":
            color = COLORS["fire"]
        elif model_name == "smoke":
            color = COLORS["smoke"]

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, cls_name, (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

def draw_fall_keypoints(frame, keypoints, alert=False):
    skeleton = [[15, 13], [13, 11], [16, 14], [14, 12],
                [11, 12], [5, 11], [6, 12], [5, 6],
                [5, 7], [6, 8], [7, 9], [8, 10],
                [1, 2], [0, 1], [0, 2], [1, 3],
                [2, 4], [3, 5], [4, 6]]

    for p1, p2 in skeleton:
        if p1 >= len(keypoints) or p2 >= len(keypoints):
            continue
        x1, y1, conf1 = keypoints[p1]
        x2, y2, conf2 = keypoints[p2]
        if conf1 > 0.5 and conf2 > 0.5:
            cv2.line(frame, (int(x1), int(y1)), (int(x2), int(y2)),
                     COLORS["fall_skeleton"], 2)

    for x, y, conf in keypoints:
        if conf > 0.5:
            cv2.circle(frame, (int(x), int(y)), 4, COLORS["fall_keypoints"], -1)

    if alert:
        head_x, head_y = keypoints[0][:2]
        cv2.putText(frame, "FALL DETECTED", (int(head_x)-40, max(int(head_y)-15, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, COLORS["fall_alert_text"], 3)

# ---------------- Video Frame Generator ----------------
# Add this import at the top
from routes.danger_zone_routes import check_person_in_danger_zone

# ---------------- Video Frame Processing ----------------
def process_frame(frame, cam_id="default"):
    """
    Processes a single frame with current models:
    - PPE / Forklift / Fire / Smoke
    - Fall detection
    - Danger Zone alert
    """
    annotated = frame.copy()
    danger_alert = False  # flag for worker in danger zone

    for model_name in CURRENT_MODELS:
        results = MODELS[model_name](annotated)

        if model_name in ["ppe", "forklift", "fire", "smoke"]:
            draw_ppe_forklift_fire_smoke(annotated, results, model_name)
        elif model_name in ["fall", "danger_zone"] and results[0].keypoints is not None:
            for idx, keypoints in enumerate(results[0].keypoints.data):
                keypoints_np = keypoints.cpu().numpy()
                track_id = int(results[0].boxes.data[idx][4])

                is_fallen = False
                if model_name == "fall":
                    is_fallen = detect_fall(keypoints_np, track_id, frame.shape[0])

                draw_fall_keypoints(annotated, keypoints_np, alert=is_fallen)

                # Danger Zone check
                if check_person_in_danger_zone(cam_id, keypoints_np,
                                            (frame.shape[1], frame.shape[0])):
                    danger_alert = True


    # Draw Danger Zone alert on top-right
    if danger_alert:
        text = "WORKER IN DANGER ZONE"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 3
        text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
        x = frame.shape[1] - text_size[0] - 20
        y = 40
        cv2.putText(annotated, text, (x, y), font, font_scale, (0, 0, 255), thickness)

    return annotated


def generate_video_frames():
    global VIDEO_PATH
    if not VIDEO_PATH or not os.path.exists(VIDEO_PATH):
        raise RuntimeError("No video uploaded yet")

    cam_id = os.path.basename(VIDEO_PATH)  # use filename as camera ID
    cap = cv2.VideoCapture(VIDEO_PATH)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        annotated = process_frame(frame, cam_id=cam_id)
        ret2, buffer = cv2.imencode(".jpg", annotated)
        if not ret2:
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
    cap.release()

# ---------------- Upload & Stream ----------------
@inference_bp.route("/upload", methods=["POST"])
def upload_video():
    global VIDEO_PATH

    if "video" not in request.files:
        return jsonify({"status": "error", "message": "No video file in request"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"}), 400

    save_dir = "uploads/videos"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, file.filename)
    file.save(save_path)

    VIDEO_PATH = save_path
    print(f"📁 Uploaded video saved to: {VIDEO_PATH}")

    return jsonify({"status": "ok", "video_path": VIDEO_PATH})

@inference_bp.route("/stream")
def stream_video():
    try:
        return Response(generate_video_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")
    except Exception as e:
        print("⚠️ Stream error:", e)
        return "No video uploaded or error occurred", 404

@inference_bp.route("/stream_rtsp")
def stream_rtsp():
    rtsp_url = request.args.get("url")
    if not rtsp_url:
        return "RTSP URL missing", 400

    def gen():
        cam_id = rtsp_url  # use RTSP URL as camera ID
        while True:
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                print(f"⚠️ Failed RTSP: {rtsp_url}. Retrying...")
                time.sleep(2)
                continue
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                annotated = process_frame(frame, cam_id=cam_id)
                ret2, buffer = cv2.imencode(".jpg", annotated)
                if not ret2:
                    continue
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            cap.release()
            time.sleep(1)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ============================================================
# 🔥 ADDITIONAL DEBUG & TERMINAL LOGGING (APPENDED)
# ============================================================

import functools
from flask import g

# ---------------- Global Frame Counters ----------------
FRAME_COUNTER = {
    "video": 0,
    "rtsp": {}
}

# ---------------- Flask Request Logs ----------------
@inference_bp.before_request
def log_request():
    g.start_time = time.time()
    print(f"➡️ [REQUEST] {request.method} {request.path}")

@inference_bp.after_request
def log_response(response):
    elapsed = (time.time() - g.start_time) * 1000
    print(f"⬅️ [RESPONSE] {request.path} | {elapsed:.2f} ms")
    return response

# ---------------- Safe Inference Wrapper ----------------
def safe_inference(model, frame):
    start = time.time()
    with torch.no_grad():
        results = model(frame)
    elapsed = (time.time() - start) * 1000
    print(f"🧠 [INFER] {model.model.names if hasattr(model, 'model') else 'model'} | {elapsed:.1f} ms")
    return results

# ---------------- Patch MODELS to Log Inference ----------------
for _name, _model in MODELS.items():
    MODELS[_name]._original_call = _model.__call__

    def _logged_call(self, *args, **kwargs):
        start = time.time()
        with torch.no_grad():
            out = self._original_call(*args, **kwargs)
        print(f"🧠 [MODEL] {id(self)} inference {(time.time()-start)*1000:.1f} ms")
        return out

    _model.__call__ = _logged_call.__get__(_model, type(_model))

print("✅ [PATCH] Inference logging enabled")

# ---------------- Danger Zone Log Hook ----------------
def log_danger(cam_id):
    print(f"⚠️ [DANGER ZONE] Worker inside zone | camera={cam_id}")

# ---------------- Fall Log Hook ----------------
def log_fall(track_id, cam_id):
    print(f" [FALL] CONFIRMED | track_id={track_id} | camera={cam_id}")

# ---------------- Wrap Original process_frame ----------------
_original_process_frame = process_frame

def process_frame(frame, cam_id="default"):
    start = time.time()
    annotated = _original_process_frame(frame, cam_id)
    elapsed = (time.time() - start) * 1000
    print(f"🎞️ [FRAME] camera={cam_id} processed in {elapsed:.1f} ms")
    return annotated

print("✅ [PATCH] process_frame wrapped with timing")

# ---------------- RTSP Connection Logs ----------------
@inference_bp.route("/health")
def health_check():
    return jsonify({
        "status": "ok",
        "models_loaded": list(MODELS.keys()),
        "active_models": CURRENT_MODELS,
        "video_loaded": VIDEO_PATH is not None
    })

print("🟢 [SYSTEM] Inference debug extensions loaded")
