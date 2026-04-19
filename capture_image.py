import cv2

cap = cv2.VideoCapture(0)

ret, frame = cap.read()

if ret:
    cv2.imwrite("live_test.jpg", frame)
    print("✅ Image captured as live_test.jpg")
else:
    print("❌ Failed to capture image")

cap.release()