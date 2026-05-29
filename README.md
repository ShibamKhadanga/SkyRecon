<p align="center">
  <img src="public/skyrecon-favicon.svg" alt="SkyRecon Logo" width="80" />
</p>

<h1 align="center">SkyRecon – AI Powered Drone Intelligence Platform</h1>

<p align="center">
  <b>Smart Aerial Mapping • Disaster Detection & Response • Real-Time Drone Analytics</b><br/>
  <em>Built for NIT Rourkela Drone Internship 2026</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React%2019%20+%20Vite-61DAFB?style=flat-square&logo=react" />
  <img src="https://img.shields.io/badge/Backend-FastAPI%200.115-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/AI-YOLOv8s-FF6F00?style=flat-square" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=flat-square&logo=postgresql" />
  <img src="https://img.shields.io/badge/Maps-Leaflet%20GIS-199900?style=flat-square&logo=leaflet" />
  <img src="https://img.shields.io/badge/CV-OpenCV-5C3EE8?style=flat-square&logo=opencv" />
</p>

---

## What is SkyRecon?

SkyRecon is a full-stack AI drone intelligence platform that processes real drone video using **YOLOv8s + OpenCV**. Upload a drone video, select what you want to detect, and the platform runs real computer vision inference frame by frame — giving you accurate object counts, area coverage in m², annotated screenshots, and downloadable PDF/DOCX reports.

### Two Core Modules

**Mapping & Survey** — Detect and count unique objects from 25 categories (vehicles, people, buildings, potholes, poles, trees, and more) from aerial footage. Uses a persistent object tracker to count each unique object only once across the entire video, regardless of how many frames it appears in.

**Disaster Response** — Scan footage for fire, flood, structural damage, fallen poles, and more. Each confirmed event gets a severity score (1–5), a screenshot from the best detection frame, auto-calculated rescue resource estimates, and an actionable recommendations report.

---

## Tech Stack

### Frontend
| Library | Purpose |
|---|---|
| React 19 + Vite | UI framework & build tool |
| TailwindCSS 4 | Styling |
| Framer Motion 12 | Animations & transitions |
| React Router DOM 7 | Client-side routing |
| Recharts 3 | Dashboard charts |
| Leaflet + React-Leaflet 5 | GIS map with detection markers |
| Lucide React | Icons |
| Zustand 5 | State management |

### Backend
| Library | Purpose |
|---|---|
| FastAPI 0.115 | REST API |
| Uvicorn | ASGI server |
| SQLAlchemy 2.0 | ORM |
| PostgreSQL + psycopg2 | Database (6 tables, 12 stored procedures) |
| **Ultralytics YOLOv8s** | Object detection AI |
| **OpenCV 4.13** | Video frame extraction & enhancement |
| **PyTorch** | Deep learning runtime |
| **NumPy** | Array/matrix operations |
| ReportLab | PDF report generation |
| python-docx | DOCX report generation |
| Pillow | Screenshot processing |

---

## Project Structure

```
SkyRecon/
├── src/                              # React frontend
│   ├── layouts/
│   │   └── AppLayout.jsx             # Sidebar + navbar shell
│   ├── components/ui/                # Reusable UI components
│   └── pages/
│       ├── LandingPage.jsx           # Module selection hub
│       ├── DashboardPage.jsx         # Analytics dashboard
│       ├── MappingPage.jsx           # AI mapping workspace
│       ├── DisasterPage.jsx          # Disaster scan workspace
│       ├── MapPage.jsx               # Leaflet GIS map
│       ├── ReportsPage.jsx           # Report browser + download
│       └── AdminPage.jsx             # Admin panel
│
└── backend/
    ├── requirements.txt              # All Python dependencies
    ├── .env                          # Environment config (create from .env.example)
    ├── .env.example                  # Config template
    ├── yolov8s.pt                    # YOLOv8s model weights (auto-downloaded)
    ├── sql/
    │   └── procedures.sql            # 12 PL/pgSQL stored procedures
    └── app/
        ├── main.py                   # FastAPI app entry point
        ├── database.py               # DB engine, session, auto-init
        ├── ai/
        │   ├── video_processor.py    # Core AI pipeline (YOLOv8 + tracker)
        │   ├── disaster_engine.py    # Disaster classification + severity scoring
        │   ├── area_calculator.py    # Bounding box → real-world m² conversion
        │   └── report_generator.py  # PDF + DOCX report builder
        ├── api/v1/
        │   ├── analysis.py           # Upload, background tasks, results, reports
        │   ├── categories.py         # Category CRUD
        │   └── dashboard.py          # Stats + map markers
        ├── core/
        │   ├── config.py             # Settings from .env
        │   └── seeder.py             # Sample data seeder for empty DB
        ├── models/models.py          # SQLAlchemy ORM models
        └── schemas/schemas.py        # Pydantic request/response schemas
```

---

## Getting Started

### Prerequisites
- Node.js ≥ 18
- Python ≥ 3.10
- PostgreSQL ≥ 14
- NVIDIA GPU with CUDA *(optional — CPU works, just slower)*

### 1. Clone & install frontend
```bash
cd SkyRecon
npm install
```

### 2. Set up backend
```bash
cd SkyRecon/backend

# Install all Python dependencies
pip install -r requirements.txt

# Create your environment config
copy .env.example .env
# Open .env and set your PostgreSQL credentials
```

### 3. Configure `.env`
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=skyrecon
DB_USER=postgres
DB_PASSWORD=your_password

YOLO_MODEL=yolov8s.pt
CONFIDENCE_THRESHOLD=0.35
```

### 4. Start both servers

**Terminal 1 — Backend:**
```bash
cd SkyRecon/backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd SkyRecon
npm run dev
```

Open **http://localhost:5173** in your browser.

> On first backend startup, it will automatically create the `skyrecon` database, all 6 tables, install all 12 stored procedures, seed the 25 detection categories, and populate sample data if the DB is empty.

> YOLOv8s model weights (`yolov8s.pt`, ~22MB) download automatically on the first analysis run.

---

## How the AI Pipeline Works

### Mapping Analysis

```
User uploads drone video + selects category (e.g. People)
        ↓
FastAPI saves file → creates DB record → launches BackgroundTask
        ↓
video_processor.py:
  1. OpenCV opens video, extracts frames at 1–2fps
  2. CLAHE contrast enhancement applied to each frame (improves aerial detection)
  3. Frame resized to 640px width for faster YOLOv8 inference
  4. YOLOv8s runs inference → detections filtered to selected category
  5. Pole detection: tall narrow bounding boxes (height/width > 3.5) → Electric Poles
  6. Persistent object tracker: each unique object counted ONCE across entire video
     - Same person walking across 50 frames = counted as 1 person
     - 3 different people = counted as 3
  7. Only first-appearance detections saved to DB (no duplicate rows)
  8. Annotated screenshots saved at detection frames
  9. Progress written to DB every 5% → frontend polls every 3s
        ↓
complete_analysis() stored procedure marks job done
        ↓
Frontend shows: unique object count, category breakdown, coverage %, area m²
        ↓
User downloads PDF or DOCX report with real data + screenshots
```

### Disaster Analysis

```
User uploads drone video
        ↓
disaster_engine.py:
  1. Same frame extraction (1fps)
  2. Classifies 7 disaster types: fire, flood, structural, people, vehicles, trees, poles
  3. Must appear in ≥ 3 sampled frames to be confirmed (eliminates noise)
  4. Severity 1–5 computed from:
       base weight (fire=5, flood=4, structural=3, others=1)
       + density bonus (more detections = higher severity)
       + area ratio bonus (large affected area)
       + confidence factor
  5. Best screenshot saved per confirmed disaster type
  6. Resource estimation auto-calculated (rescue teams, ambulances, boats, staff)
        ↓
Frontend shows confirmed events with screenshots + resource table
Voice alert fires ONLY for fire or flood at severity ≥ 4
PDF/DOCX report downloadable
```

---

## Detection Categories (25)

| Category | YOLO Classes Used |
|---|---|
| Vehicles | car, truck, bus, motorcycle, bicycle, boat, airplane |
| People | person, backpack, umbrella, handbag + accessories |
| Plants | potted plant, banana, apple, orange, broccoli, carrot |
| Trees | detected via vegetation context |
| Electric Poles | fire hydrant, parking meter + tall narrow aspect ratio heuristic |
| Traffic Lights | traffic light |
| Roads | stop sign context |
| Road Potholes | road surface analysis |
| Water Bodies | boat context + flood detection |
| Buildings | bench, chair, tv, laptop, keyboard + indoor objects |
| Houses | bed, couch |
| Parking Areas | vehicle density analysis |
| Garbage Areas | bottle, cup, fork, knife, spoon, bowl, wine glass, food items |
| Construction Zones | site context |
| Agricultural Land | crop field context |
| Animals | cat, dog, horse, cow, sheep, bird, elephant, bear, zebra, giraffe |
| Solar Panels | rooftop context |
| Bridges | structural context |
| Railway Tracks | train |
| Fire & Smoke | fire/flame triggers |
| Flood Water | boat + water accumulation |
| Shops | commercial context |
| Warehouses | industrial context |
| Pipelines | pipeline context |
| Street Lights | tall narrow aspect ratio heuristic |

> **Note on Poles & Street Lights:** YOLOv8 has no native "pole" class. SkyRecon detects them using a bounding-box aspect ratio heuristic — any detection taller than 3.5× its width is classified as a pole/street light.

---

## API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/api/docs`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | API status + GPU availability |
| `POST` | `/api/v1/analysis/upload` | Upload video, start AI pipeline |
| `GET` | `/api/v1/analysis/{id}/status` | Poll processing progress (0–100%) |
| `GET` | `/api/v1/analysis/{id}/summary` | Full results — unique counts, coverage, breakdown |
| `GET` | `/api/v1/analysis/{id}/detections` | All unique detections (filterable by category) |
| `GET` | `/api/v1/analysis/{id}/disasters` | All confirmed disaster events |
| `POST` | `/api/v1/analysis/{id}/report` | Generate PDF or DOCX report |
| `GET` | `/api/v1/analysis/report/{id}/status` | Report generation status |
| `GET` | `/api/v1/analysis/report/{id}/download` | Download generated report file |
| `GET` | `/api/v1/analysis/reports/` | List all completed analyses for Reports page |
| `DELETE` | `/api/v1/analysis/{id}` | Delete analysis + all related data |
| `GET` | `/api/v1/categories/` | List all 25 detection categories |
| `GET` | `/api/v1/dashboard/stats` | Platform-wide statistics |
| `GET` | `/api/v1/dashboard/recent-analyses` | Recent analysis jobs |
| `GET` | `/api/v1/dashboard/map-markers` | GIS map markers |

---

## Database Schema

6 tables, 12 PL/pgSQL stored procedures.

```
categories ──── characteristics   (1:N)
categories ──── detections        (1:N)
analyses   ──── detections        (1:N, cascade delete)
analyses   ──── disaster_events   (1:N)
analyses   ──── reports           (1:N)
```

### Stored Procedures
| Procedure | Purpose |
|---|---|
| `create_analysis_job()` | Register new analysis job, return ID |
| `record_detection()` | Insert one unique detection row |
| `record_disaster_event()` | Insert disaster event + auto-calculate rescue resources |
| `complete_analysis()` | Mark analysis done with timing + object count |
| `get_dashboard_stats()` | Aggregate platform-wide statistics |
| `get_recent_analyses()` | Return N most recent jobs |
| `generate_report_record()` | Create report row, return ID |
| `mark_report_ready()` | Mark report ready + store file path |
| `delete_analysis_cascade()` | Safe delete analysis + all related data |
| `search_detections()` | Full-text search across detection labels |
| `upsert_category()` | Insert or update a detection category |
| `seed_default_categories()` | Idempotent seed of all 25 categories |

---

## Choosing a YOLO Model

| Model | Size | Speed | Accuracy | Recommended For |
|---|---|---|---|---|
| `yolov8n.pt` | 6 MB | Fastest | Lower | Development / testing only |
| `yolov8s.pt` | 22 MB | Fast | Good | **Default — balanced CPU performance** |
| `yolov8m.pt` | 52 MB | Medium | Better | GPU machines, production use |

Set `YOLO_MODEL=yolov8s.pt` in `.env`. The model downloads automatically on first use.

---

## Accuracy Notes

- **People counting** uses a persistent IoU-based object tracker. Each person is counted exactly once — when they first appear in the video. The same person walking across 60 seconds of footage is still counted as 1.
- **Pole detection** uses a bounding-box aspect ratio heuristic since YOLOv8 has no native pole class. Objects with height/width > 3.5 are classified as Electric Poles or Street Lights.
- **Disaster severity** is calibrated so normal people/vehicles in a video do not trigger emergency alerts. Only confirmed fire or flood at severity ≥ 4 triggers the voice alarm.
- **Frame enhancement** — CLAHE contrast equalization + mild sharpening is applied to every frame before inference to improve detection on hazy or low-contrast aerial footage.
- **Confidence thresholds** are tuned per category: People use 0.30 (harder to detect from altitude), Vehicles use 0.40, others use 0.35–0.40.

---

## Responsive Design

- **Mobile** — hamburger menu opens sidebar as overlay with dark backdrop
- **Tablet** — sidebar collapses to icon-only mode
- **Desktop** — full sidebar with labels, all grids expand to multi-column layout

---

## Known Limitations

- YOLOv8 is trained on COCO dataset (80 classes). Categories like "potholes", "solar panels", "warehouses", and "agricultural land" are approximated through class mapping and heuristics — not natively detected.
- Processing speed on CPU: approximately 1–2 minutes per minute of 1080p video at 1fps sampling.
- GPU (CUDA) reduces processing time by ~5–10×.

---

<p align="center">
  <b>SkyRecon</b> – <em>AI Powered Aerial Intelligence & Disaster Monitoring Platform</em><br/>
  Built with ❤️ at NIT Rourkela · 2026 Drone Internship
</p>
