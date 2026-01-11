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
print(f"🔥 Using device: {DEVICE}")

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
                     (255, 255, 0), 1)
    for kp in keypoints:
        x, y, conf = kp
        if conf > confidence_threshold:
            cv2.circle(frame, (int(x), int(y)), 3, (0, 0, 255), -1)

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

    # Update angle change
    angle_change = abs(spine_angle - fall_states[track_id].get('last_spine_angle', spine_angle))
    fall_states[track_id]['last_spine_angle'] = spine_angle

    # Update position history
    current_time = time.time()
    if current_time - fall_states[track_id]['last_update_time'] > 0.01:
        fall_states[track_id]['position_history'].append(center)
        fall_states[track_id]['last_update_time'] = current_time
        if len(fall_states[track_id]['position_history']) > 10:
            fall_states[track_id]['position_history'].pop(0)

    # Calculate speed
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

    # Track stillness
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

    # Update fall states
    if is_fall_candidate:
        fall_states[track_id]['falling_frames'] += 2
        fall_states[track_id]['confirmation_frames'] += 1
        if fall_states[track_id]['fall_start_time'] is None:
            fall_states[track_id]['fall_start_time'] = current_time
    else:
        fall_states[track_id]['falling_frames'] = max(0, fall_states[track_id]['falling_frames'] - 1)
        fall_states[track_id]['confirmation_frames'] = 0
        fall_states[track_id]['fall_start_time'] = None

    # Confirm fall after threshold
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

    # Reset fall states if fall not selected
    if "fall" not in CURRENT_MODELS:
        fall_states.clear()

    return jsonify({"status": "ok", "models": CURRENT_MODELS})


# ---------------- Video Frame Generator ----------------
def process_frame(frame):
    annotated = frame.copy()
    for model_name in CURRENT_MODELS:
        results = MODELS[model_name](annotated)

        # Fall detection
        if model_name == "fall" and results[0].keypoints is not None:
            for idx, keypoints in enumerate(results[0].keypoints.data):
                keypoints_np = keypoints.cpu().numpy()
                track_id = int(results[0].boxes.data[idx][4])
                if detect_fall(keypoints_np, track_id, frame.shape[0]):
                    box = results[0].boxes.data[idx][:4].cpu().numpy()
                    cv2.rectangle(annotated,
                                  (int(box[0]), int(box[1])),
                                  (int(box[2]), int(box[3])),
                                  (0, 0, 255), 2)
                    cv2.putText(annotated, 'FALL DETECTED',
                                (int(box[0]), int(box[1]-10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,255), 2)

        annotated = results[0].plot()
    return annotated


def generate_video_frames():
    global VIDEO_PATH
    if not VIDEO_PATH or not os.path.exists(VIDEO_PATH):
        raise RuntimeError("No video uploaded yet")

    cap = cv2.VideoCapture(VIDEO_PATH)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
        annotated = process_frame(frame)
        ret2, buffer = cv2.imencode(".jpg", annotated)
        if not ret2:
            continue
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
    cap.release()


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
                annotated = process_frame(frame)
                ret2, buffer = cv2.imencode(".jpg", annotated)
                if not ret2:
                    continue
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            cap.release()
            time.sleep(1)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")
