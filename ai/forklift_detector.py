from ai.model_loader import ModelLoader

def run_forklift_detection(frame):
    model = ModelLoader.get_forklift_model()
    results = model(frame, conf=0.4, iou=0.5)
    return results
