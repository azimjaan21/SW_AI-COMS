import time
from flask import Blueprint, request, jsonify
from shapely.geometry import Point, Polygon

# ================= Blueprint =================
danger_bp = Blueprint("danger", __name__)

# ================= In-memory storage =================
# Structure:
# {
#   "camera_id": [
#       [[x_norm, y_norm], [x_norm, y_norm], ...],   # polygon 1
#       [[x_norm, y_norm], ...]                      # polygon 2
#   ]
# }
DANGER_ZONES = {}

# ================= CRUD ROUTES =================

@danger_bp.route("/", methods=["GET"])
def list_zones():
    """
    GET /danger-zones/?camera_id=1
    """
    camera_id = request.args.get("camera_id")
    if not camera_id:
        return jsonify([])

    zones = DANGER_ZONES.get(str(camera_id), [])
    return jsonify([{"points": z} for z in zones])


@danger_bp.route("/", methods=["POST"])
def add_zone():
    """
    POST /danger-zones/
    Body:
    {
        "camera_id": "1",
        "points": [[0.1,0.2], [0.5,0.2], [0.5,0.6], [0.1,0.6]]
    }
    """
    data = request.json
    camera_id = str(data.get("camera_id"))
    points = data.get("points")

    if not camera_id or not points:
        return jsonify({
            "status": "error",
            "message": "camera_id and points are required"
        }), 400

    if camera_id not in DANGER_ZONES:
        DANGER_ZONES[camera_id] = []

    DANGER_ZONES[camera_id].append(points)

    print(f"[INFO] Danger zone added | Camera: {camera_id}")
    return jsonify({"status": "ok"})


@danger_bp.route("/delete_all/<camera_id>/", methods=["DELETE"])
def delete_all(camera_id):
    """
    DELETE /danger-zones/delete_all/1/
    """
    DANGER_ZONES[str(camera_id)] = []
    print(f"[INFO] All danger zones deleted | Camera: {camera_id}")
    return jsonify({"status": "ok"})


# ================= DANGER ZONE CHECK =================

def check_person_in_danger_zone(camera_id, keypoints, frame_dims):
    """
    Check if ANY confident keypoint is inside ANY danger polygon.

    Args:
        camera_id (str|int)
        keypoints (np.ndarray): shape (17, 3) -> [x, y, conf]
        frame_dims (tuple): (width, height)

    Returns:
        bool
    """
    width, height = frame_dims
    zones = DANGER_ZONES.get(str(camera_id), [])

    if not zones:
        return False

    for zone_points in zones:
        # Convert normalized coords -> absolute
        polygon = Polygon([
            (x * width, y * height) for x, y in zone_points
        ])

        for x, y, conf in keypoints:
            if conf > 0.5 and polygon.contains(Point(x, y)):
                return True

    return False
