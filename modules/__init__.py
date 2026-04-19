# Smart Attendance System — modules package
from .face_recognizer import load_known_faces, recognize_faces, get_image_path_for_id
from .attendance_manager import (
    initialize,
    mark_attendance,
    save_unknown_face,
    get_attendance_records,
    copy_known_face_to_static,
)
