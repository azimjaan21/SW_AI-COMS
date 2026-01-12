# danger_zone_routes.py
import os
import json
import time
from flask import Blueprint, request, jsonify
from shapely.geometry import Point, Polygon

danger_bp = Blueprint("danger", __name__)

# Store polygons in memory for now (can switch to DB)
DANGER_ZONES = {}  # {camera_id: [polygon1, polygon2,...]}

# ---------------- CRUD ----------------
@danger_bp.route("/", methods=["GET"])
def list_zones():
    camera_id = request.args.get("camera_id")
    if not camera_id:
        return jsonify([])

    zones = DANGER_ZONES.get(camera_id, [])
    return jsonify([{"points": z} for z in zones])

@danger_bp.route("/", methods=["POST"])
def add_zone():
    data = request.json
    camera_id = str(data.get("camera_id"))
    points = data.get("points")  # [[x_norm, y_norm], ...]

    if not camera_id or not points:
        return jsonify({"status": "error", "message": "camera_id and points required"}), 400

    if camera_id not in DANGER_ZONES:
        DANGER_ZONES[camera_id] = []

    DANGER_ZONES[camera_id].append(points)
    return jsonify({"status": "ok"})

@danger_bp.route("/delete_all/<camera_id>/", methods=["DELETE"])
def delete_all(camera_id):
    DANGER_ZONES[camera_id] = []
    return jsonify({"status": "ok"})

# ---------------- Danger Zone Check ----------------
def check_person_in_danger_zone(camera_id, keypoints, frame_dims):
    """
    keypoints: numpy array of shape (17,3) - [x, y, conf]
    frame_dims: (width, height)
    Returns True if any keypoint inside any polygon
    """
    width, height = frame_dims
    zones = DANGER_ZONES.get(str(camera_id), [])
    if not zones:
        return False

    for zone_points in zones:
        # convert normalized to absolute coords
        poly = Polygon([(x * width, y * height) for x, y in zone_points])
        for kp in keypoints:
            x, y, conf = kp
            if conf > 0.5 and poly.contains(Point(x, y)):
                return True
    return False
