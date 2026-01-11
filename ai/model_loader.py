from ultralytics import YOLO
import os
from config import MODEL_FOLDER

class ModelLoader:
    _models = {}

    @classmethod
    def load_model(cls, name, weight_file):
        if name not in cls._models:
            weight_path = os.path.join(MODEL_FOLDER, weight_file)
            cls._models[name] = YOLO(weight_path)
        return cls._models[name]

    @classmethod
    def get_ppe_model(cls):
        return cls.load_model("ppe", "ppe.pt")

    @classmethod
    def get_fire_model(cls):
        return cls.load_model("fire", "fire.pt")

    @classmethod
    def get_forklift_model(cls):
        return cls.load_model("forklift", "forklift.pt")

    @classmethod
    def get_pose_model(cls):
        return cls.load_model("pose", "yolo11s-pose.pt")
