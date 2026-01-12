import os
from flask import Flask, send_from_directory
from flask_cors import CORS

# Config import
from config import UPLOAD_FOLDER

# Blueprints
from routes.main_routes import main_bp
from routes.upload_routes import upload_bp
from routes.inference_routes import inference_bp
from routes.zone_routes import danger_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object("config")
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    # Enable CORS for frontend access
    CORS(app)

    # Ensure necessary folders exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs("uploads/videos", exist_ok=True)
    os.makedirs("outputs/processed", exist_ok=True)

    # Register Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp, url_prefix="/api/upload")
    app.register_blueprint(inference_bp, url_prefix="/api/inference")
    app.register_blueprint(danger_bp, url_prefix="/api/zones")

    # Serve uploaded videos statically
    @app.route("/uploads/videos/<path:filename>")
    def serve_video(filename):
        return send_from_directory("uploads/videos", filename)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
