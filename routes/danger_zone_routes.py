import time
from flask import Blueprint, request, jsonify
from shapely.geometry import Point, Polygon

danger_bp = Blueprint("danger", __name__)

# ================= CONFIG =================
ALERT_COOLDOWN_SECONDS = 3.0
KEYPOINT_CONF_TH = 0.5

# ================= STORAGE =================
DANGER_ZONES = {}

# Per-camera alert state
LAST_ALERT_TIME = {}            # camera_id -> timestamp
PERSON_ZONE_STATE = {}          # camera_id -> { person_id: inside_bool }

# ================= CRUD =================

@danger_bp.route("/", methods=["GET"])
def list_zones():
    camera_id = request.args.get("camera_id")
    if not camera_id:
        return jsonify([])

    return jsonify([
        {"points": z}
        for z in DANGER_ZONES.get(str(camera_id), [])
    ])


@danger_bp.route("/", methods=["POST"])
def add_zone():
    data = request.json
    camera_id = str(data.get("camera_id"))
    points = data.get("points")

    if not camera_id or not points:
        return jsonify({"status": "error"}), 400

    DANGER_ZONES.setdefault(camera_id, []).append(points)
    print(f"🟥 Zone added | cam={camera_id}")
    return jsonify({"status": "ok"})


@danger_bp.route("/delete_all/<camera_id>/", methods=["DELETE"])
def delete_all(camera_id):
    DANGER_ZONES[str(camera_id)] = []
    PERSON_ZONE_STATE.pop(str(camera_id), None)
    print(f"🗑 Zones cleared | cam={camera_id}")
    return jsonify({"status": "ok"})


# ================= CORE LOGIC =================

def _cooldown_passed(camera_id):
    now = time.time()
    last = LAST_ALERT_TIME.get(camera_id, 0)
    if now - last >= ALERT_COOLDOWN_SECONDS:
        LAST_ALERT_TIME[camera_id] = now
        return True
    return False


def check_persons_in_danger_zone(camera_id, persons_keypoints, frame_dims):
    """
    Args:
        camera_id: str
        persons_keypoints: list of np.array (17,3) per person
        frame_dims: (width, height)

    Returns:
        bool -> alert trigger
    """
    camera_id = str(camera_id)
    zones = DANGER_ZONES.get(camera_id, [])
    if not zones:
        return False

    width, height = frame_dims
    PERSON_ZONE_STATE.setdefault(camera_id, {})

    alert_triggered = False

    for person_idx, keypoints in enumerate(persons_keypoints):
        inside_now = False

        for zone in zones:
            polygon = Polygon([
                (x * width, y * height)
                for x, y in zone
            ])

            for x, y, conf in keypoints:
                if conf < KEYPOINT_CONF_TH:
                    continue
                if polygon.contains(Point(float(x), float(y))):
                    inside_now = True
                    break

            if inside_now:
                break

        prev_state = PERSON_ZONE_STATE[camera_id].get(person_idx, False)

        # 🔥 ENTER event
        if inside_now and not prev_state:
            if _cooldown_passed(camera_id):
                print(f"⚠️ ALERT | cam={camera_id} person={person_idx}")
                alert_triggered = True

        PERSON_ZONE_STATE[camera_id][person_idx] = inside_now

    return alert_triggered
