# AI-Based Smart Attendance System using Face Recognition and ESP32-CAM 🚀

## Description 📝

This project is an AI-powered attendance system that uses advanced face recognition and anti-spoofing techniques to automatically mark attendance. It integrates a modern web-based interface (Flask), deep learning models for face verification, and ESP32-CAM for real-time image capture with IoT interaction.

The system ensures secure attendance by distinguishing real faces from spoofs (photos, screens, masks) and provides real-time feedback through LEDs and web dashboard.

## Features ✨

- 🔍 **Real-time Face Detection & Recognition** using face_recognition library
- 🛡️ **Anti-Spoofing Detection** - Distinguishes real faces from photos/screens/videos
- 📊 **Automatic Attendance Marking** with timestamps in Excel format
- 📱 **Web Dashboard** for live monitoring and manual overrides
- 📹 **ESP32-CAM Integration** for wireless camera streaming
- 💡 **IoT LED Feedback** (Green=Valid, Red=Invalid/Spoof)
- ⏰ **Time-Restricted Attendance** (Present before 9 AM, Late after)
- ⚡ **Optimized Performance** with frame skipping and caching

## Tech Stack 🛠️

| Frontend      | Backend       | AI/ML                                      | Hardware  | Other            |
| ------------- | ------------- | ------------------------------------------ | --------- | ---------------- |
| HTML, CSS, JS | Python, Flask | OpenCV, TensorFlow/Keras, face_recognition | ESP32-CAM | Pandas, Openpyxl |

## System Architecture 🏗️

```
ESP32-CAM → MJPEG Stream → Flask App → AI Processing → Attendance Excel
                    ↓
                Web Dashboard (Live Feed + Records)
                    ↓
                LED/Buzzer Feedback via HTTP API
```

**Flow:**

1. ESP32-CAM streams video to Flask server
2. Frame → Face Detection (HOG) → Anti-Spoof (Deep Learning) → Recognition
3. Valid face → Mark attendance → Update Excel → Trigger green LED
4. Spoof/Unknown → Red LED + Save unknown face image

## Folder Structure 📁

```
AI_Attendance_System/
├── app.py                    # Main Flask application + AI pipeline
├── modules/
│   ├── face_recognizer.py   # Face encoding & recognition logic
│   └── attendance_manager.py # Excel handling & duplicate prevention
├── models/
│   └── anti_spoof.h5        # Trained anti-spoofing model
├── templates/                # HTML templates (index.html, iot.html)
├── static/                   # CSS, JS, profile images
├── known_faces/              # Dataset folders (per person)
├── esp32_attendance.ino      # ESP32-CAM firmware
├── requirements.txt          # Python dependencies
├── attendance.xlsx           # Attendance records (auto-generated)
└── README.md
```

## Installation Guide 🚀

### Prerequisites

- Python 3.8+
- ESP32-CAM with Arduino IDE
- Webcam access (for testing)

### Step 1: Clone & Setup Python Environment

```bash
git clone <your-repo>
cd AI_Attendance_System
python -m venv venv
# Windows
venv\\Scripts\\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Prepare Dataset

```
known_faces/
├── Hannan/
│   ├── img1.jpg
│   └── img2.jpg
├── Person2/
│   └── *.jpg
```

Add 2-5 photos per person in separate folders.

### Step 3: ESP32 Setup

See [ESP32 Setup Instructions](#esp32-setup-instructions) below.

### Step 4: Run Application

```bash
python app.py
```

Open http://localhost:5000

## Usage Instructions 🎮

1. **Live Monitoring**: Visit `http://localhost:5000` for live feed
2. **Attendance Records**: View `/api/records` or dashboard
3. **Manual Entry**: POST to `/manual` endpoint
4. **IoT Panel**: `http://localhost:5000/iot` for LED controls

## ESP32 Setup Instructions 🔌

1. **Hardware Wiring**:

   ```
   ESP32-CAM → LED (Green D2, Red D4) → Buzzer (D15)
   Power: 5V/2A recommended
   ```

2. **Arduino IDE Setup**:
   - Install ESP32 board support
   - Upload `esp32_attendance.ino`
   - Configure WiFi credentials
   - Enable camera web server on port 80

3. **Network**:
   - Update `ESP32_IP` in `app.py` to your ESP32 IP
   - Ensure same network as server

## How Attendance System Works ⚙️

1. **Face Detection** → HOG algorithm locates faces
2. **Anti-Spoof Check** → CNN model scores real/fake (threshold 0.5)
3. **Recognition** → Compare encodings vs known database (tolerance 0.48)
4. **Mark Attendance** → Excel append if first entry today
5. **Status Logic** → "Present" (<9AM) or "Late" (>=9AM)

## Anti-Spoofing Explanation 🕵️

Uses MobileNetV2 + custom head trained on:

- **Real**: Live faces, various lighting
- **Fake**: Printouts, screens, replay videos

**Techniques**:

- Laplacian texture variance
- Motion analysis
- Histogram equalization
- Multiple validation frames

Accuracy: ~95% on test set.

## Future Improvements 🚀

- [ ] Mobile app integration
- [ ] Cloud sync (Google Sheets)
- [ ] Multi-camera support
- [ ] Face liveness detection (blink detection)
- [ ] Role-based access (student vs admin)
- [ ] Email/SMS notifications
- [ ] Database migration (SQLite/PostgreSQL)

## Screenshots 📸

![Dashboard](screenshots/dashboard.png)
![Live Feed](screenshots/live-feed.png)
![ESP32 Setup](screenshots/esp32-setup.png)
![Attendance Records](screenshots/records.png)

_Note: Screenshots coming soon_

## Author 👤

**Mohamed Hannan**  
Full-Stack AI Developer  
[LinkedIn](https://linkedin.com/in/yourprofile) | [GitHub](https://github.com/yourusername)  
📧 mohamed@example.com

---

⭐ **Star this repo if you found it useful!**  
📢 **Contributions welcome via pull requests!**
