import cv2

def video_frame_generator(video_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError("Cannot open video")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        yield frame

    cap.release()
