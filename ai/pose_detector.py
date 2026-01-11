from ai.model_loader import ModelLoader

def run_pose_detection(frame):
    model = ModelLoader.get_pose_model()
    results = model(frame, conf=0.4)
    return results
