# 🧠 Smart AI Attendance System

A **production-grade AI attendance system** powered by real-time face recognition,
built with OpenCV, face_recognition (dlib ResNet), Flask, and a sleek dark-theme dashboard.

---

## ✨ Features

| Feature | Detail |
|---|---|
| **Face Recognition** | dlib ResNet model via `face_recognition` library |
| **Real-time Detection** | OpenCV webcam stream, ~30fps |
| **Bounding Boxes** | Green (recognized) / Red (unknown) |
| **Attendance Logging** | Excel (attendance.xlsx) with Name, ID, Time, Date, Status |
| **Status Logic** | Present (before 09:00) / Late (after 09:00) |
| **Duplicate Prevention** | Same ID logged only once per day |
| **Unknown Faces** | Auto-saved to `unknown_faces/` folder |
| **Web Dashboard** | Live MJPEG stream + attendance log + stats |
| **Auto-refresh** | Dashboard polls every 2 seconds |
| **Mobile-friendly** | Responsive grid layout |

---

## 🏗 Project Structure

```
smart_attendance/
├── app.py                    # Flask app + camera thread
├── add_face.py               # Helper: register faces via webcam
├── requirements.txt
│
├── modules/
│   ├── __init__.py
│   ├── face_recognizer.py    # Face encoding + recognition
│   └── attendance_manager.py # Excel logging + unknown saving
│
├── templates/
│   └── index.html            # Dashboard HTML
│
├── static/
│   ├── css/style.css         # Dark theme stylesheet
│   ├── js/dashboard.js       # Auto-refresh + card rendering
│   └── images/               # Known-face thumbnails (auto-populated)
│
├── known_faces/              # Add your face images here!
│   └── saad_101.jpg          # Format: name_id.jpg
│
├── unknown_faces/            # Auto-saved unknown faces
└── attendance.xlsx           # Auto-created attendance log
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
# macOS
brew install cmake
pip install -r requirements.txt

# Ubuntu / Debian
sudo apt-get install cmake libboost-all-dev python3-dev
pip install -r requirements.txt

# Windows
# Install Visual Studio Build Tools (C++ workload), then:
pip install cmake dlib
pip install -r requirements.txt
```

### 2. Add known faces

**Option A — Use the helper script:**
```bash
python add_face.py --name saad --id 101
python add_face.py --name alice --id 102
```

**Option B — Add manually:**
Place `.jpg` images in `known_faces/` using the naming format:
```
known_faces/
  saad_101.jpg
  alice_102.jpg
  john_doe_103.jpg   # Multi-word names supported
```

> **Note:** Each image must contain exactly one clearly visible face.

### 3. Run the app

```bash
python app.py
```

Open your browser: **http://localhost:5000**

---

## 🎛 Configuration

Edit constants in `app.py`:

| Variable | Default | Description |
|---|---|---|
| `UNKNOWN_SAVE_COOLDOWN` | `10` | Seconds between saving the same unknown face |
| `process_every_n` | `3` | Process recognition every N frames (higher = faster but less responsive) |

Edit constants in `modules/attendance_manager.py`:

| Variable | Default | Description |
|---|---|---|
| `CUTOFF_TIME` | `09:00:00` | Before this = Present, after = Late |

Edit tolerance in `modules/face_recognizer.py`:

```python
recognize_faces(frame, known_data, tolerance=0.50)
# Lower tolerance = stricter matching (fewer false positives)
# Recommended range: 0.45–0.55
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Dashboard UI |
| `/video_feed` | GET | MJPEG camera stream |
| `/api/records` | GET | All attendance records (JSON) |
| `/api/stats` | GET | Today's summary stats (JSON) |

---

## 📋 attendance.xlsx Format

| Name | ID | Time | Date | Status |
|---|---|---|---|---|
| Saad Affan | 101 | 08:45:12 | 2025-01-15 | Present |
| Alice Smith | 102 | 09:15:33 | 2025-01-15 | Late |

---

## ⚙️ How It Works

```
Webcam Frame (OpenCV)
       │
       ▼
  Resize to 25% ──→ face_recognition.face_locations()
                           │
                           ▼
                  face_recognition.face_encodings()
                           │
                           ▼
              Compare with known encodings (cosine distance)
                     │               │
              distance ≤ 0.50    distance > 0.50
                     │               │
              ┌──────┘               └──────────┐
              ▼                                  ▼
     Mark Attendance (Excel)          Save unknown face image
     Draw green bounding box          Draw red bounding box
```

---

## 🛠 Troubleshooting

**"No known faces loaded"**
→ Add images to `known_faces/` following the `name_id.jpg` format.

**Camera not opening**
→ Check `VideoCapture(0)`. If you have multiple cameras, try `VideoCapture(1)`.

**Slow performance**
→ Increase `process_every_n` in `app.py` (e.g., from 3 to 5).

**dlib installation fails**
→ Make sure cmake is installed before running pip install.

---

## 📄 License

MIT — Free to use for academic, portfolio, and personal projects.
