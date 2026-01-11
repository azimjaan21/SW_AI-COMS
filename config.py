import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Paths
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads", "videos")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs", "processed")
MODEL_FOLDER = os.path.join(BASE_DIR, "models")

# Flask
SECRET_KEY = "aicoms-secret-key"
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB video upload

# Video
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov"}

# Detection thresholds
CONF_THRESHOLD = 0.4
IOU_THRESHOLD = 0.5
