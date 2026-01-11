from ai.model_loader import ModelLoader

def run_ppe_detection(frame):
    model = ModelLoader.get_ppe_model()
    results = model(frame, conf=0.4, iou=0.5)
    return results
