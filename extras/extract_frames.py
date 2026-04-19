import cv2
import os

def extract(input_folder, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if file.endswith(".mp4"):
            cap = cv2.VideoCapture(os.path.join(input_folder, file))
            count = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if count % 10 == 0:
                    name = f"{file}_{count}.jpg"
                    cv2.imwrite(os.path.join(output_folder, name), frame)

                count += 1

            cap.release()
            print("Done:", file)

# REAL
extract("dataset/real/live_video", "dataset_final/real")

# FAKE
extract("dataset/fake/replay", "dataset_final/fake")
extract("dataset/fake/printouts", "dataset_final/fake")
extract("dataset/fake/cut-out printouts", "dataset_final/fake")