from flask import Flask, send_from_directory
from flask_cors import CORS

from config import UPLOAD_FOLDER
from routes.main_routes import main_bp
from routes.upload_routes import upload_bp
from routes.inference_routes import inference_bp
from routes.zone_routes import zone_bp

import os


def create_app():
    app = Flask(__name__)
    app.config.from_object("config")
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    # Enable CORS
    CORS(app)

    # Ensure folders exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs("outputs/processed", exist_ok=True)

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp, url_prefix="/api/upload")
    app.register_blueprint(inference_bp, url_prefix="/api/inference")
    app.register_blueprint(zone_bp, url_prefix="/api/zones")

    # Serve uploaded videos
    @app.route("/uploads/videos/<path:filename>")
    def serve_video(filename):
        return send_from_directory("uploads/videos", filename)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
