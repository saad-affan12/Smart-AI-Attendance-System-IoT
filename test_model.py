import cv2
import numpy as np
from tensorflow.keras.models import load_model

model = load_model("models/anti_spoof.h5")

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    img = cv2.resize(frame, (224, 224))
    img = img / 255.0
    img = np.expand_dims(img, axis=0)

    pred = model.predict(img)[0][0]

    if pred > 0.3:
        label = "REAL ✅"
        color = (0, 255, 0)
    else:
        label = "FAKE ❌"
        color = (0, 0, 255)

    cv2.putText(frame, f"{label} ({pred:.2f})", (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    cv2.imshow("Anti-Spoofing", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()