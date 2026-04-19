"""
face_recognizer.py
------------------
Handles loading known face encodings from a folder-based dataset and
performing face recognition on incoming frames.

Expected dataset layout:
    known_faces/
        PersonA/
            img1.jpg
            img2.jpg
        PersonB/
            img1.jpg
"""

import os
import logging

import cv2
import face_recognition
import numpy as np

logger = logging.getLogger(__name__)


def load_known_faces(dataset_path: str) -> dict:
    """
    Scan the known_faces/ directory and encode every image found.

    Returns:
        dict with keys:
            'encodings' -> list of 128-d face encodings
            'names' -> list of person names (str)
            'ids' -> list of person IDs (str)
            'image_paths' -> list of original file paths (for dashboard)
    """
    encodings_list = []
    names_list = []
    ids_list = []
    image_paths = []

    if not os.path.exists(dataset_path):
        logger.error(f"Dataset path '{dataset_path}' does not exist.")
        return {"encodings": [], "names": [], "ids": [], "image_paths": []}

    supported_exts = (".jpg", ".jpeg", ".png", ".bmp")
    person_id = 0

    for person_name in sorted(os.listdir(dataset_path)):
        person_folder = os.path.join(dataset_path, person_name)

        if not os.path.isdir(person_folder):
            continue

        logger.info("[INFO] Loading person: %s", person_name)
        folder_has_face = False
        current_person_id = str(person_id)

        for filename in sorted(os.listdir(person_folder)):
            if not filename.lower().endswith(supported_exts):
                continue

            filepath = os.path.join(person_folder, filename)

            try:
                img = face_recognition.load_image_file(filepath)
                face_encs = face_recognition.face_encodings(img)

                if not face_encs:
                    logger.warning("[WARNING] No face in %s", filepath)
                    continue

                encodings_list.append(face_encs[0])
                names_list.append(person_name)
                ids_list.append(current_person_id)
                image_paths.append(filepath)
                folder_has_face = True
                logger.info("Loaded: %s (ID: %s) from %s", person_name, current_person_id, filename)
            except Exception as exc:
                logger.error("Error processing '%s': %s", filepath, exc)

        if folder_has_face:
            person_id += 1

    logger.info("[INFO] Loaded %s people", len(set(names_list)))
    return {
        "encodings": encodings_list,
        "names": names_list,
        "ids": ids_list,
        "image_paths": image_paths,
    }


def recognize_faces(
    frame: np.ndarray,
    known_data: dict,
    tolerance: float = 0.50,
    model: str = "hog",
    apply_lighting_normalization: bool = True,
):
    """
    Detect and recognize all faces in a single small BGR frame.

    Args:
        frame: small BGR image already resized for speed
        known_data: dict returned by load_known_faces()
        tolerance: lower = stricter matching
        model: face detector model for face_recognition.face_locations
        apply_lighting_normalization: equalize brightness before detection

    Returns:
        list of dicts, one per detected face:
            {
                'name': str,
                'id': str,
                'top': int, 'right': int, 'bottom': int, 'left': int,
                'recognized': bool
            }
    """
    if frame is None or frame.size == 0:
        return []

    processed_frame = frame

    if apply_lighting_normalization:
        ycrcb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2YCrCb)
        ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
        processed_frame = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

    rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame, model=model)

    if not face_locations:
        return []

    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    results = []

    for enc, loc in zip(face_encodings, face_locations):
        name = "Unknown"
        person_id = "N/A"
        recognized = False

        if known_data["encodings"]:
            distances = face_recognition.face_distance(known_data["encodings"], enc)
            best_idx = int(np.argmin(distances))

            if distances[best_idx] < tolerance:
                name = known_data["names"][best_idx]
                person_id = known_data["ids"][best_idx]
                recognized = True

        top, right, bottom, left = loc
        results.append(
            {
                "name": name,
                "id": person_id,
                "top": top,
                "right": right,
                "bottom": bottom,
                "left": left,
                "recognized": recognized,
            }
        )

    return results


def get_image_path_for_id(known_data: dict, person_id: str) -> str | None:
    """Return the original dataset image path for a given person ID."""
    for i, pid in enumerate(known_data["ids"]):
        if pid == person_id:
            return known_data["image_paths"][i]
    return None
