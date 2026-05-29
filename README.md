<p align="center">
  <img src="public/skyrecon-favicon.svg" alt="SkyRecon Logo" width="80" />
</p>

<h1 align="center">SkyRecon – AI Powered Drone Intelligence Platform</h1>

<p align="center">
  <b>Smart Aerial Mapping • Disaster Detection & Response • Real-Time Drone Analytics</b><br/>
  <em>Built for NIT Rourkela Drone Internship 2026</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React%20+%20Vite-61DAFB?style=flat-square&logo=react" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/AI-YOLOv8-FF6F00?style=flat-square" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=flat-square&logo=postgresql" />
  <img src="https://img.shields.io/badge/Maps-Leaflet%20GIS-199900?style=flat-square&logo=leaflet" />
  <img src="https://img.shields.io/badge/CV-OpenCV-5C3EE8?style=flat-square&logo=opencv" />
</p>

---

## What is SkyRecon?

SkyRecon is a full-stack AI drone intelligence platform that **actually processes drone video** using YOLOv8 + OpenCV. Upload a drone video, select what you want to detect, and the platform runs real computer vision inference — frame by frame — and gives you a detailed report with real numbers, real area coverage, and real screenshots.

Two core modules:

- **Mapping & Survey** — detect vehicles, people, plants, buildings, potholes, and 21 other categories from aerial footage. Get real object counts, area coverage in m², and downloadable PDF/DOCX reports.
- **Disaster Response** — scan footage for floods, fire, structural damage, fallen poles, and more. Each event gets a severity level (1–5), a screenshot from the exact video frame, resource estimates, and an actionable report.

---

## Tech Stack

### Frontend
| | |
|---|---|
| React 19 + Vite 8 | UI framework & build tool |
| TailwindCSS 4 | Styling |
| Framer Motion 12 | Animations & transitions |
| React Router DOM 7 | Client-side routing |
| Recharts 3 | Dashboard charts |
| Leaflet + React-Leaflet 5 | GIS map |
| Lucide React | Icons |
| Zustand 5 | State management |

### Backend
| | |
|---|---|
| FastAPI 0.115 | REST API |
| Uvicorn | ASGI server |
| SQLAlchemy 2.0 | ORM |
| PostgreSQL + psycopg2 | Database |
| **Ultralytics YOLOv8** | Object detection AI |
| **OpenCV** | Video frame extraction |
| **PyTorch** | Deep learning runtime |
| **NumPy** | Array/matrix operations |
| ReportLab | PDF generation |
| python-docx | DOCX generation |
| Pillow | Screenshot processing |

---

## Project Structure

```
SkyRecon/
├── src/                          # React frontend
│   ├── layouts/
│   │   └── AppLayout.jsx         # Sidebar + navbar shell (mobile responsive)
│   ├── components/
│   │   ├── Sidebar.jsx           # Collapsible nav sidebar
│   │   └── ui/                   # Reusable components
│   └── pages/
│       ├── LandingPage.jsx       # Module selection hub
│       ├── DashboardPage.jsx     # Analytics dashboard
│       ├── MappingPage.jsx       # ← Real AI mapping workspace
│       ├── DisasterPage.jsx      # ← Real disaster scan workspace
│       ├── MapPage.jsx           # GIS map (Leaflet)
│       ├── ReportsPage.jsx       # Report browser
│       └── AdminPage.jsx         # Admin panel
│
└── backend/
    ├── requirements.txt          # All Python dependencies
    ├── .env                      # Your environment config
    ├── .env.example              # Template
    ├── sql/
    │   └── procedures.sql        # 12 PL/pgSQL stored procedures
    └── app/
        ├── main.py               # FastAPI app entry point
        ├── database.py           # DB engine, session, init
        ├── ai/                   # ← The AI heart of the project
        │   ├── video_processor.py    # OpenCV + YOLOv8 mapping pipeline
        │   ├── disaster_engine.py    # Disaster classification + severity
        │   ├── area_calculator.py    # Bounding box → real m² conversion
        │   └── report_generator.py   # Real PDF + DOCX from DB data
        ├── api/v1/
        │   ├── analysis.py       # Upload, background tasks, results, reports
        │   ├── categories.py     # Category CRUD
        │   └── dashboard.py      # Stats + map markers
        ├── core/
        │   ├── config.py         # Settings (env vars)
        │   └── seeder.py         # Mock data seeder for empty DB
        ├── models/models.py      # SQLAlchemy ORM (6 tables)
        └── schemas/schemas.py    # Pydantic schemas
```

---

## Getting Started

### Prerequisites
- Node.js ≥ 18
- Python ≥ 3.10
- PostgreSQL ≥ 14
- (Optional but recommended) NVIDIA GPU with CUDA for faster inference

### 1. Frontend
```bash
cd SkyRecon
npm install
npm run dev
# Runs on http://localhost:5173
# Vite proxies /api/* → http://localhost:8000 automatically
```

### 2. Backend
```bash
cd SkyRecon/backend

# Install all dependencies (YOLOv8, OpenCV, PyTorch, FastAPI...)
pip install -r requirements.txt

# Configure your database
cp .env.example .env
# Edit .env — set DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Start the server
uvicorn app.main:app --reload --port 8000
```

On first startup the server will:
1. Auto-create the `skyrecon` PostgreSQL database if it doesn't exist
2. Create all 6 tables
3. Install all 12 PL/pgSQL stored procedures
4. Seed the 25 default detection categories
5. Seed sample analyses/detections if the DB is empty

YOLOv8 model weights (`yolov8n.pt`, ~6MB) download automatically on first analysis run.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `skyrecon` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| `YOLO_MODEL` | `yolov8n.pt` | Model weights — use `yolov8s.pt` or `yolov8m.pt` for better accuracy |
| `CONFIDENCE_THRESHOLD` | `0.5` | Minimum detection confidence (0.0–1.0) |
| `UPLOAD_DIR` | `./uploads` | Where uploaded videos are saved |
| `REPORTS_DIR` | `./reports` | Where generated reports are saved |
| `SCREENSHOTS_DIR` | `./screenshots` | Where detection screenshots are saved |

---

## How the AI Pipeline Works

### Mapping Analysis
```
User uploads video
       ↓
FastAPI saves file → creates DB record → launches BackgroundTask
       ↓
video_processor.py:
  OpenCV opens video → extracts frames at 2fps
  YOLOv8 runs inference on each frame
  YOLO class names mapped to 25 SkyRecon categories
  Filtered by user's selected category + characteristics
  Bounding boxes saved → area_calculator converts to real m²
  Annotated screenshots saved every 50 detections
  All detections persisted via record_detection() stored procedure
       ↓
Frontend polls /api/v1/analysis/{id}/status every 3s
       ↓
On completion → /api/v1/analysis/{id}/summary returns:
  real detection count, category breakdown, coverage %, area m²
       ↓
User clicks PDF/DOCX → report_generator.py builds real report from DB
```

### Disaster Analysis
```
User uploads video
       ↓
disaster_engine.py:
  Same frame extraction
  Classifies disaster types: fire, flood, structural, people, vehicles, trees, poles
  Requires detection in ≥2 frames (eliminates single-frame noise)
  Severity 1–5 computed from: type weight + detection density + area ratio + confidence
  Best frame screenshot saved per disaster type
  Persisted via record_disaster_event() → auto-calculates rescue resources
       ↓
Frontend shows real events with real screenshots
Voice alert triggered via Web Speech API for critical events
Real PDF/DOCX report downloadable
```

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | API status + GPU availability |
| `POST` | `/api/v1/analysis/upload` | Upload video, start AI pipeline |
| `GET` | `/api/v1/analysis/{id}/status` | Poll processing status |
| `GET` | `/api/v1/analysis/{id}/summary` | Full results with coverage stats |
| `GET` | `/api/v1/analysis/{id}/detections` | All detections (filterable by category) |
| `GET` | `/api/v1/analysis/{id}/disasters` | All disaster events |
| `POST` | `/api/v1/analysis/{id}/report` | Generate PDF or DOCX report |
| `GET` | `/api/v1/analysis/report/{id}/status` | Report generation status |
| `GET` | `/api/v1/analysis/report/{id}/download` | Download generated report |
| `GET` | `/api/v1/categories/` | List all 25 detection categories |
| `GET` | `/api/v1/dashboard/stats` | Platform-wide statistics |
| `GET` | `/api/v1/dashboard/recent-analyses` | Recent analysis jobs |
| `GET` | `/api/v1/dashboard/map-markers` | GIS map markers |

Interactive docs: `http://localhost:8000/api/docs`

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

### Key Stored Procedures
| Procedure | Purpose |
|---|---|
| `create_analysis_job()` | Register new analysis |
| `record_detection()` | Insert detection + auto-increment counter |
| `record_disaster_event()` | Insert disaster event + auto-calculate resources |
| `complete_analysis()` | Mark done with timing stats |
| `get_dashboard_stats()` | Aggregate platform stats |
| `delete_analysis_cascade()` | Safe delete with all related data |
| `seed_default_categories()` | Idempotent 25-category seed |

---

## Detection Categories (25)

Vehicles, People, Plants, Trees, Electric Poles, Traffic Lights, Roads, Road Potholes, Water Bodies, Buildings, Houses, Parking Areas, Garbage Areas, Construction Zones, Agricultural Land, Animals, Solar Panels, Bridges, Railway Tracks, Fire & Smoke, Flood Water, Shops, Warehouses, Pipelines, Street Lights

---

## Choosing a YOLO Model

| Model | Size | Speed | Accuracy | Recommended For |
|---|---|---|---|---|
| `yolov8n.pt` | 6 MB | Fastest | Good | Development, CPU-only machines |
| `yolov8s.pt` | 22 MB | Fast | Better | Balanced performance |
| `yolov8m.pt` | 52 MB | Medium | Best of these | GPU machines, production |

Set `YOLO_MODEL=yolov8s.pt` in `.env` for better real-world accuracy.

---

## Responsive Design

The UI is fully responsive across all screen sizes:
- **Mobile** — hamburger menu opens sidebar as overlay with dark backdrop
- **Tablet** — sidebar collapses to icon-only mode
- **Desktop** — full sidebar with labels, all grids expand to multi-column

---

<p align="center">
  <b>SkyRecon</b> – <em>AI Powered Aerial Intelligence & Disaster Monitoring Platform</em><br/>
  Built with ❤️ at NIT Rourkela · 2026 Drone Internship
</p>
