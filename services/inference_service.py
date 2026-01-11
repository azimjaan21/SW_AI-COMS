from ai.ppe_detector import run_ppe_detection
from ai.fire_detector import run_fire_detection
from ai.forklift_detector import run_forklift_detection
from ai.pose_detector import run_pose_detection


def run_inference(frame, selected_modules):
    """
    frame: numpy image
    selected_modules: list[str]
    """

    annotated_frame = frame.copy()

    # PPE
    if "ppe" in selected_modules:
        results = run_ppe_detection(annotated_frame)
        annotated_frame = results[0].plot()

    # Fire
    if "fire" in selected_modules:
        results = run_fire_detection(annotated_frame)
        annotated_frame = results[0].plot()

    # Forklift
    if "forklift" in selected_modules:
        results = run_forklift_detection(annotated_frame)
        annotated_frame = results[0].plot()

    # Pose (Danger Zone / Fall later)
    if "danger_zone" in selected_modules or "fall" in selected_modules:
        results = run_pose_detection(annotated_frame)
        annotated_frame = results[0].plot()

    return annotated_frame
