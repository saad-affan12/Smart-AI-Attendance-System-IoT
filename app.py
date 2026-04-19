import os
import sys
import time
import threading
import logging
import datetime

import cv2
import face_recognition
import numpy as np
import pandas as pd
import requests
from flask import Flask, Response, jsonify, render_template, request
from tensorflow.keras.models import load_model

sys.path.insert(0, os.path.dirname(__file__))

from modules.face_recognizer import load_known_faces, recognize_faces
from modules.attendance_manager import (
    initialize as init_attendance,
    mark_attendance,
    get_attendance_records,
    copy_known_face_to_static,
)


# ---------------- CONFIG ----------------
DATASET_DIR = "known_faces"
STATIC_IMAGES_DIR = os.path.join("static", "images")

ESP32_IP = "http://10.32.125.142/"
ESP_IP = "http://10.32.125.142/"
ESP32_TIMEOUT = 1

FRAME_SKIP = 2
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CPU_COOLDOWN = 0.001
RECOGNITION_TOLERANCE = 0.48
JPEG_QUALITY = 95

ESP32_STREAM_URL = "http://10.32.125.142/stream"
CAMERA_WARMUP_SECONDS = 1.0
CAMERA_RETRY_DELAY = 1.0

MOVEMENT_THRESHOLD = 5
MAX_STATIC_FRAMES = 12
REAL_THRESHOLD = 0.75
MOVEMENT_BONUS = 0.3


# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

app = Flask(__name__)
cv2.setUseOptimized(True)
spoof_model = load_model("models/anti_spoof.h5")


# ---------------- GLOBAL STATE ----------------
_frame_lock = threading.Lock()
_latest_frame = None
_known_data = {}

last_face_center = None
no_movement_counter = 0
marked_ids = set()
last_state = None
prev_gray = None
motion_score = 0
last_labels = {}
last_face_data = {}
last_trigger_time = 0
TRIGGER_DELAY = 2
last_time = time.time()

latest_data = {
    "name": "Waiting",
    "id": "",
    "status": "",
    "time": "",
    "date": "",
}


# ---------------- IOT TRIGGER ----------------
def _normalize_base_url(url):
    return url.rstrip("/")


ESP32_BASE_URL = _normalize_base_url(ESP32_IP)
ESP_BASE_URL = _normalize_base_url(ESP_IP)


def trigger_iot(event):
    for _ in range(2):
        try:
            requests.get(f"{ESP32_BASE_URL}/{event}", timeout=ESP32_TIMEOUT)
            logger.info("IoT triggered: %s", event)
            return
        except requests.RequestException:
            time.sleep(0.3)
    logger.warning("IoT device not responding")


def update_led_state(state):
    global last_state

    if last_state == state:
        return

    try:
        requests.get(f"{ESP_BASE_URL}/{state}", timeout=0.5)
        last_state = state
    except requests.RequestException:
        pass


def safe_trigger(endpoint):
    global last_trigger_time

    if time.time() - last_trigger_time < TRIGGER_DELAY:
        return

    try:
        requests.get(f"{ESP_BASE_URL}/{endpoint}", timeout=0.5)
        last_trigger_time = time.time()
        logger.info("ESP32 Trigger: %s", endpoint)
    except Exception:
        pass


# ---------------- DETECTION + SPOOF ----------------
def detect_faces(frame):
    if frame is None or frame.size == 0:
        return []

    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
    normalized = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    rgb_frame = cv2.cvtColor(normalized, cv2.COLOR_BGR2RGB)
    return face_recognition.face_locations(rgb_frame, model="hog")


def predict_spoof_score(frame, face):
    try:
        top = max(0, int(face["top"]))
        right = min(frame.shape[1], int(face["right"]))
        bottom = min(frame.shape[0], int(face["bottom"]))
        left = max(0, int(face["left"]))

        if right <= left or bottom <= top:
            return 0.0

        face_img = frame[top:bottom, left:right]
        if face_img.size == 0:
            return 0.0

        face_resized = cv2.resize(face_img, (224, 224), interpolation=cv2.INTER_LINEAR)
        face_resized = face_resized.astype("float32") / 255.0
        face_resized = np.expand_dims(face_resized, axis=0)

        return float(spoof_model.predict(face_resized, verbose=0)[0][0])
    except Exception as exc:
        logger.exception("Anti-spoof prediction failed: %s", exc)
        return 1.0


def get_texture_score(face_img):
    gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()


def _bbox_iou(box_a, box_b):
    left = max(box_a["left"], box_b["left"])
    top = max(box_a["top"], box_b["top"])
    right = min(box_a["right"], box_b["right"])
    bottom = min(box_a["bottom"], box_b["bottom"])

    if right <= left or bottom <= top:
        return 0.0

    intersection = (right - left) * (bottom - top)
    area_a = max(1, (box_a["right"] - box_a["left"]) * (box_a["bottom"] - box_a["top"]))
    area_b = max(1, (box_b["right"] - box_b["left"]) * (box_b["bottom"] - box_b["top"]))
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def match_face(face, recognized_faces, used_matches):
    best_idx = None
    best_score = 0.0

    for idx, candidate in enumerate(recognized_faces):
        if idx in used_matches:
            continue

        score = _bbox_iou(face, candidate)
        if score > best_score:
            best_score = score
            best_idx = idx

    if best_idx is None or best_score <= 0.1:
        return None

    used_matches.add(best_idx)
    return recognized_faces[best_idx]


# ---------------- DRAW ----------------
def annotate(frame, faces):
    for face in faces:
        top = max(0, int(face.get("top", 0)))
        right = min(frame.shape[1], int(face.get("right", 0)))
        bottom = min(frame.shape[0], int(face.get("bottom", 0)))
        left = max(0, int(face.get("left", 0)))
        label = face.get("label", "Unknown")
        debug_text = face.get("debug")
        color = tuple(face.get("color", (0, 0, 255)))

        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(
            frame,
            label,
            (left, max(20, top - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            color,
            2,
        )
        if debug_text:
            cv2.putText(
                frame,
                debug_text,
                (left, min(frame.shape[0] - 10, bottom + 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

    return frame


# ---------------- CAMERA THREAD ----------------
def camera_thread():
    global _latest_frame, latest_data, last_face_center, no_movement_counter
    global prev_gray, motion_score, last_labels, last_face_data, last_time

    logger.info("ESP32 camera thread started")
    processed_faces = []
    frame_count = 0

    while True:
        cap = cv2.VideoCapture(ESP32_STREAM_URL, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            logger.error("Unable to open ESP32 stream: %s", ESP32_STREAM_URL)
            time.sleep(CAMERA_RETRY_DELAY)
            continue

        time.sleep(CAMERA_WARMUP_SECONDS)
        logger.info("ESP32 stream connected")

        try:
            while True:
                ret, raw_frame = cap.read()
                if not ret or raw_frame is None or raw_frame.size == 0:
                    logger.warning("ESP32 frame read failed; reconnecting")
                    cap.release()
                    time.sleep(CAMERA_RETRY_DELAY)
                    cap = cv2.VideoCapture(ESP32_STREAM_URL, cv2.CAP_FFMPEG)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if not cap.isOpened():
                        logger.error("Unable to reopen ESP32 stream: %s", ESP32_STREAM_URL)
                        continue
                    time.sleep(CAMERA_WARMUP_SECONDS)
                    prev_gray = None
                    continue

                frame = cv2.resize(
                    raw_frame,
                    (FRAME_WIDTH, FRAME_HEIGHT),
                    interpolation=cv2.INTER_LINEAR,
                )
                display_frame = frame.copy()
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                current_time = time.time()
                elapsed = max(current_time - last_time, 1e-6)
                fps = 1.0 / elapsed
                last_time = current_time

                if prev_gray is not None:
                    diff = cv2.absdiff(prev_gray, gray)
                    motion_score = diff.mean()

                prev_gray = gray
                frame_count += 1
                try:
                    processed_faces = []
                    recognized_in_frame = False
                    spoof_detected = False
                    detected_locations = detect_faces(frame)
                    seen_keys = set()

                    if not detected_locations:
                        last_face_center = None
                        no_movement_counter = 0
                        last_labels = {}
                        last_face_data = {}
                        update_led_state("red")
                    else:
                        for top, right, bottom, left in detected_locations:
                            top = max(0, int(top))
                            right = min(frame.shape[1], int(right))
                            bottom = min(frame.shape[0], int(bottom))
                            left = max(0, int(left))

                            x = left
                            y = top
                            w = right - left
                            h = bottom - top

                            if w <= 0 or h <= 0:
                                continue

                            face_img = frame[y:y + h, x:x + w]
                            if face_img.size == 0:
                                continue

                            key = (x, y, w, h)
                            seen_keys.add(key)
                            should_validate = (frame_count % FRAME_SKIP == 0) or (key not in last_face_data)

                            if should_validate:
                                texture_score = get_texture_score(face_img)
                                cached_face = last_face_data.get(key, {})

                                if frame_count % 3 == 0 or "spoof_score" not in cached_face:
                                    model_face = cv2.resize(face_img, (160, 160))
                                    spoof_input = model_face.astype("float32") / 255.0
                                    spoof_input = np.expand_dims(spoof_input, axis=0)

                                    try:
                                        spoof_score = float(spoof_model.predict(spoof_input, verbose=0)[0][0])
                                    except Exception as exc:
                                        logger.exception("Anti-spoof prediction failed: %s", exc)
                                        spoof_score = 1.0
                                else:
                                    spoof_score = float(cached_face.get("spoof_score", 1.0))

                                if motion_score > 15:
                                    spoof_score = min(spoof_score, 0.3)

                                is_real = spoof_score < 0.5

                                if motion_score > 5:
                                    is_real = True

                                if texture_score < 10:
                                    is_real = False

                                print(
                                    f"[FINAL] S:{spoof_score:.2f} M:{motion_score:.2f} "
                                    f"T:{texture_score:.2f} -> REAL:{is_real}"
                                )

                                if key in last_labels:
                                    prev = last_labels[key]
                                    if prev == "REAL" and not is_real:
                                        is_real = True

                                last_labels[key] = "REAL" if is_real else "FAKE"

                                current_face = {
                                    "name": "Unknown",
                                    "id": "N/A",
                                    "top": top,
                                    "right": right,
                                    "bottom": bottom,
                                    "left": left,
                                    "recognized": False,
                                    "color": (0, 0, 255),
                                    "label": "Face",
                                    "debug": f"S:{spoof_score:.2f} M:{motion_score:.1f} T:{texture_score:.0f}",
                                }

                                if is_real:
                                    recognition_results = recognize_faces(
                                        face_img,
                                        _known_data,
                                        tolerance=RECOGNITION_TOLERANCE,
                                        model="hog",
                                        apply_lighting_normalization=True,
                                    )

                                    if recognition_results:
                                        best_match = recognition_results[0]
                                        current_face["name"] = best_match["name"]
                                        current_face["id"] = best_match["id"]
                                        current_face["recognized"] = best_match["recognized"]

                                    name = current_face["name"]
                                    pid = current_face["id"]
                                    current_face["label"] = f"{name} ({pid})"
                                    current_face["color"] = (0, 255, 0)

                                    if current_face["recognized"] and name != "Unknown":
                                        recognized_in_frame = True

                                        if pid not in marked_ids:
                                            attendance_marked = mark_attendance(name, pid)
                                            if attendance_marked:
                                                marked_ids.add(pid)
                                                now = datetime.datetime.now()
                                                status = "Late" if now.hour >= 9 else "Present"
                                                latest_data = {
                                                    "name": name,
                                                    "id": pid,
                                                    "status": status,
                                                    "time": now.strftime("%H:%M:%S"),
                                                    "date": now.strftime("%Y-%m-%d"),
                                                }
                                                trigger_iot("present" if status == "Present" else "late")
                                            else:
                                                marked_ids.add(pid)
                                else:
                                    spoof_detected = True

                                last_face_data[key] = {
                                    "name": current_face["name"],
                                    "id": current_face["id"],
                                    "recognized": current_face["recognized"],
                                    "label": current_face["label"],
                                    "color": current_face["color"],
                                    "debug": current_face["debug"],
                                    "spoof_score": spoof_score,
                                    "texture_score": texture_score,
                                }
                            else:
                                cached_face = last_face_data.get(key)
                                current_face = {
                                    "name": "Unknown",
                                    "id": "N/A",
                                    "top": top,
                                    "right": right,
                                    "bottom": bottom,
                                    "left": left,
                                    "recognized": False,
                                    "label": "Face",
                                    "color": (0, 0, 255),
                                    "debug": None,
                                }
                                if cached_face:
                                    current_face.update(cached_face)
                                    if current_face.get("recognized") and current_face.get("name") != "Unknown":
                                        recognized_in_frame = True
                                    if current_face.get("label") == "SPOOF":
                                        spoof_detected = True

                            processed_faces.append(current_face)

                        last_labels = {key: last_labels[key] for key in seen_keys if key in last_labels}
                        last_face_data = {
                            key: last_face_data[key] for key in seen_keys if key in last_face_data
                        }
                        update_led_state("green" if recognized_in_frame else "red")
                        if spoof_detected:
                            safe_trigger("spoof")
                        elif recognized_in_frame:
                            safe_trigger("green")
                        else:
                            safe_trigger("red")
                except Exception as exc:
                    logger.exception("Recognition pipeline error: %s", exc)

                cv2.putText(
                    display_frame,
                    f"FPS: {int(fps)}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )
                annotated_frame = annotate(display_frame, processed_faces)
                success, jpeg = cv2.imencode(
                    ".jpg",
                    annotated_frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
                )

                if success:
                    with _frame_lock:
                        _latest_frame = jpeg.tobytes()

                time.sleep(CPU_COOLDOWN)
        finally:
            cap.release()
            time.sleep(CAMERA_RETRY_DELAY)


# ---------------- STREAM ----------------
def gen_frames():
    while True:
        with _frame_lock:
            frame = _latest_frame

        if frame is not None:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        else:
            time.sleep(0.03)


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/iot")
def iot():
    return render_template("iot.html", esp_stream="")


@app.route("/video_feed")
def video_feed():
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=face",
    )


@app.route("/api/records")
def records():
    return jsonify(get_attendance_records())


@app.route("/api/latest")
def latest():
    return jsonify(latest_data)


# ---------------- MANUAL ----------------
@app.route("/manual", methods=["POST"])
def manual():
    data = request.json
    df = pd.read_excel("attendance.xlsx")

    new = {
        "Name": data["name"],
        "ID": data["id"],
        "Date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "Time": datetime.datetime.now().strftime("%H:%M:%S"),
        "Status": "Present",
    }

    df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
    df.to_excel("attendance.xlsx", index=False)

    return {"status": "ok"}


# ---------------- EDIT ----------------
@app.route("/edit", methods=["POST"])
def edit():
    data = request.json
    df = pd.read_excel("attendance.xlsx")

    df.loc[df["ID"].astype(str) == str(data["id"]), "Status"] = data["status"]
    df.to_excel("attendance.xlsx", index=False)

    return {"status": "updated"}


# ---------------- START ----------------
if __name__ == "__main__":
    _known_data = load_known_faces(DATASET_DIR)
    init_attendance()

    for i, pid in enumerate(_known_data.get("ids", [])):
        src = _known_data["image_paths"][i]
        copy_known_face_to_static(src, STATIC_IMAGES_DIR, pid)

    threading.Thread(target=camera_thread, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
