# test_rtsp_live.py
import cv2

rtsp_url = "rtsp://admin:dalab$123@10.198.137.122:554/stream1"  # <-- put your RTSP URL here

cap = cv2.VideoCapture(rtsp_url)

if not cap.isOpened():
    print("❌ Failed to connect to RTSP stream!")
else:
    print("✅ Connected to RTSP stream. Press 'q' to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Failed to read frame from RTSP stream.")
            break

        cv2.imshow("RTSP Live Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
