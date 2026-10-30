# Crowd Safety Monitor
**Operations Intelligence Platform**

An enterprise-grade, AI-driven surveillance dashboard designed to proactively detect crowd disasters, stampedes, and compressive asphyxia risks in real-time.

## Features

- **Real-Time Telemetry**: 10Hz WebSocket streaming for instant UI updates with zero latency.
- **Hardware Acceleration**: Apple Silicon MPS GPU support dropping YOLOv8 inference to 25ms (20+ FPS throughput).
- **Multi-Camera Instant Switcher**: 1-click toggling between `CAM-01` (Mall 40p dense concourse), `CAM-02` (Temple bottleneck queue), `CAM-03` (Shibuya pedestrian crossing), and hardware `WEBCAM` (hotkeys `1`, `2`, `3`).
- **4×4 Spatial Zone Matrix**: Real-time 16-zone visual matrix tracking local micro-density, speed, and identifying active choke points.
- **Dual-Tone Synthesized Audio Alerts**: Web Audio API harmonic alarm chimes (880Hz / 587Hz) with instant mute toggles (`[M]` key).
- **Density Heatmap & Flow Vectors**: Live Gaussian kernel heatmap (`[H]`) and Farnebäck Optical Flow motion vectors (`[F]`) burned onto the feed.
- **Asphyxia & Crush Modeling**: Physics-calibrated velocity decay curve and time-integrated compressive asphyxia hazard index ($S_z[t]$).
- **Post-Incident Audit Report**: One-click official session summary (`/report_page`) detailing temporal risk progression ($R_z[t]$), peak crowd metrics, asphyxia indices, auto-captured evidence gallery, and printable PDF audit dossier.
- **Final Viva Presentation Decks**: Ready-to-present 14-slide widescreen presentation deck (`Crowd_Safety_Monitor_Final_Review.pptx`) and high-resolution PDF (`Crowd_Safety_Monitor_Final_Review.pdf`).

## Project Team & Mentorship
- **Student Authors**:
  - **Kumar Prathmesh** (Reg. No: `24BEC0680`)
  - **Manan Rastogi** (Reg. No: `24BML0004`)
  - **Jayanth Anand** (Reg. No: `24BML0072`)
- **Faculty Guide & Evaluator**:
  - **Prof. / Dr. Jeeva Devakumar** (Faculty Guide & Evaluator)

## Project Deliverable Generation

The repository includes standalone Python generators to compile academic documentation and presentation materials on demand:

- **Official Project-1 Report**: Run `python build_official_project_report_2026.py` to compile the calibrated report (`.docx` and `.pdf`).
- **Evaluation Presentation**: Run `python build_evaluation_deck_and_paper.py` to build the 16:9 widescreen evaluation deck (`.pptx` and `.pdf`).
- **Academic Research Paper**: Run `python generate_academic_paper.py` to render the single-column research paper (`.html`, `.pdf`, and `.md`).

## Tech Stack

- **Backend**: FastAPI, WebSockets, Python 3.12, Uvicorn
- **AI/CV**: OpenCV, PyTorch (Apple Silicon MPS), Ultralytics (YOLOv8), NumPy
- **Frontend**: HTML5, Vanilla JavaScript, Tailwind CSS, Web Audio API

## Installation

1. Clone the repository and navigate to the project directory.
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Start the FastAPI server:

```bash
python -m uvicorn fastapi_app:app --host 0.0.0.0 --port 8080
```

Then, open your browser and navigate to `http://localhost:8080`.

**Interactive Controls:**
- Press `1`, `2`, `3` to switch cameras (Mall Concourse, Queue, Shibuya Crossing).
- Press `F` to toggle Farnebäck Optical Flow motion vectors.
- Press `H` to toggle Density Heatmap overlay.
- Press `M` to toggle Audio Alarm Chimes.
- Click **"Audit Report"** in top bar to open `/report_page` and export court-admissible PDF audit dossiers.

## Architecture Notes
The application runs the heavy OpenCV processing loop in a non-blocking daemon thread. This ensures the ASGI web server remains responsive to WebSocket connections and HTTP requests while the AI models process video frames at maximum speed.