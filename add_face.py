"""
add_face.py
-----------
Quick helper to register a new person from your webcam.

Usage:
    python add_face.py --name saad --id 101

This will:
  1. Open the webcam
  2. Display the live feed
  3. Press SPACE to capture and save to known_faces/saad_101.jpg
  4. Press Q to quit
"""

import argparse
import cv2
import os
import sys


def capture_face(name: str, person_id: str, output_dir: str = "known_faces"):
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("ERROR: Cannot open webcam.")
        sys.exit(1)

    print(f"\nCapturing face for: {name} (ID: {person_id})")
    print("  SPACE → Capture and save")
    print("  Q     → Quit without saving\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame capture failed.")
            break

        display = frame.copy()
        cv2.putText(
            display,
            f"Name: {name}  ID: {person_id}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 200, 80),
            2,
        )
        cv2.putText(
            display,
            "SPACE: Capture | Q: Quit",
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),
            1,
        )

        cv2.imshow("Register Face — Smart Attendance", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(" "):
            filename = f"{name.lower()}_{person_id}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            print(f"✔  Saved: {filepath}")
            break
        elif key == ord("q"):
            print("Cancelled.")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register a new face for attendance.")
    parser.add_argument("--name", required=True, help="Person's name (e.g. saad)")
    parser.add_argument("--id",   required=True, help="Person's ID  (e.g. 101)")
    parser.add_argument("--dir",  default="known_faces", help="Output directory")
    args = parser.parse_args()

    capture_face(args.name, args.id, args.dir)
