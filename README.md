<p align="center">
  <img src="public/skyrecon-favicon.svg" alt="SkyRecon Logo" width="80" />
</p>

<h1 align="center">SkyRecon – AI Powered Drone Intelligence Platform</h1>

<p align="center">
  <b>Smart Aerial Mapping • Disaster Detection & Response • Real-Time Drone Analytics</b><br/>
  <em>Built for NIT Rourkela Drone Internship 2026</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React%2019%20+%20Vite%208-61DAFB?style=flat-square&logo=react" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/AI-YOLOv8%20+%20ByteTrack-FF6F00?style=flat-square" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=flat-square&logo=postgresql" />
  <img src="https://img.shields.io/badge/Maps-Leaflet%20GIS-199900?style=flat-square&logo=leaflet" />
  <img src="https://img.shields.io/badge/Segmentation-SegFormer--B2-764ABC?style=flat-square" />
</p>

---

## What is SkyRecon?

SkyRecon is a full-stack AI drone intelligence platform that **actually processes drone video** using a multi-model AI pipeline. Upload a drone video or image, select what you want to detect, and the platform runs real computer vision inference frame by frame and gives you a detailed report with real counts, area coverage, and per-object screenshots.

Two core modules:

- **Mapping & Survey** — detect 25 categories from aerial footage using specialized fine-tuned models. Get real unique object counts via ByteTrack, area coverage in m², one cropped screenshot per unique object with timestamp, and downloadable PDF/DOCX reports.
- **Disaster Response** — scan footage for floods, fire, structural damage, fallen poles. Each event gets severity 1-5, a screenshot from the exact video frame, resource estimates, and an actionable report.

---

## AI Models

SkyRecon uses 4 specialized fine-tuned models alongside base YOLOv8:

| Model File | Trained On | Best For |
|---|---|---|
| `skyrecon_visdrone.pt` | VisDrone2019 | People & vehicles from aerial view |
| `skyrecon_rdd2022.pt` | RDD2022 Road Damage | Potholes, road cracks |
| `skyrecon_fire_smoke.pt` | Fire/Smoke dataset | Fire detection, smoke plumes |
| `skyrecon_flood.pt` | Flood imagery | Flood water, inundated areas |
| `skyrecon_trees_plants.pt` | Aerial vegetation | Trees & plants |
| `yolov8s.pt` | COCO (general) | Fallback for all other categories |
| `yolov8n.pt` | COCO (general) | Fast fallback |
| `yolov8x.pt` | COCO (general) | High accuracy fallback |

The pipeline automatically selects the best model per category.

---

## Detection Pipeline

**YOLO-detectable categories** (People, Vehicles, Animals...):
```
Frame → CLAHE Enhancement → Resize 640px → YOLOv8 + ByteTrack
     → Aerial misclassification fix (kite→person etc.)
     → Characteristics filter (2-Wheeler, color, etc.)
     → Unique object tracking (one count per track ID)
     → Cropped screenshot per new unique object
```

**Aerial-specific categories** (Trees, Water, Buildings, Roads, Fire...):
```
Frame → SegFormer-B2 segmentation + OpenCV heuristics
     → ExG vegetation index (trees/plants)
     → HSV color analysis (fire, water, solar panels)
     → Edge detection (poles, bridges, pipelines)
     → Grid-based deduplication
```

---

## Tech Stack

### Frontend
| | |
|---|---|
| React 19 + Vite 8 | UI + build |
| TailwindCSS 4 | Styling |
| Framer Motion 12 | Animations |
| React Router DOM 7 | Routing |
| Recharts 3 | Charts |
| Leaflet + React-Leaflet 5 | GIS map |
| Lucide React | Icons |

### Backend
| | |
|---|---|
| FastAPI | REST API |
| SQLAlchemy 2.0 + PostgreSQL | Database |
| Ultralytics YOLOv8 | Detection + ByteTrack tracking |
| OpenCV | Frame extraction + heuristic detection |
| PyTorch | Deep learning runtime |
| SegFormer-B2 (HuggingFace) | Aerial semantic segmentation |
| ReportLab + python-docx | PDF + DOCX report generation |

---

## Project Structure

```
SkyRecon/
├── index.html                    # Entry HTML
├── package.json                  # Frontend dependencies
├── vite.config.js                # Vite bundler + proxy config
├── tsconfig.json                 # TypeScript configuration
├── src/                          # React frontend
│   ├── main.jsx                  # App entry point
│   ├── App.jsx                   # Routes (7 pages)
│   ├── index.css                 # Global styles + Tailwind
│   ├── layouts/
│   │   └── AppLayout.jsx         # Sidebar + navbar (mobile responsive)
│   ├── components/
│   │   ├── Sidebar.jsx           # Navigation sidebar
│   │   └── ui/                   # Reusable UI components
│   │       ├── AnimatedCounter.jsx
│   │       ├── ConfidenceBar.jsx
│   │       ├── FileDropzone.jsx
│   │       ├── GlassCard.jsx
│   │       ├── NeonButton.jsx
│   │       ├── RadarPulse.jsx
│   │       ├── SeverityBadge.jsx
│   │       └── StatCard.jsx
│   └── pages/
│       ├── LandingPage.jsx       # Module selection landing
│       ├── DashboardPage.jsx     # Statistics dashboard
│       ├── MappingPage.jsx       # Upload + config + results (mapping)
│       ├── DisasterPage.jsx      # Upload + config + results (disaster)
│       ├── MapPage.jsx           # GIS map with markers + heatmaps
│       ├── ReportsPage.jsx       # Report listing + download
│       └── AdminPage.jsx         # Category & system management
│
├── public/
│   └── skyrecon-favicon.svg      # App favicon
│
└── backend/
    ├── requirements.txt          # Python dependencies
    ├── .env.example              # Environment variable template
    ├── sql/
    │   └── procedures.sql        # 12 PL/pgSQL stored procedures
    ├── app/
    │   ├── __init__.py
    │   ├── main.py               # FastAPI app + CORS + routes
    │   ├── database.py           # SQLAlchemy engine + init
    │   ├── ai/
    │   │   ├── video_processor.py    # Full mapping pipeline
    │   │   ├── disaster_engine.py    # Disaster classification
    │   │   ├── area_calculator.py    # bbox → real m²
    │   │   └── report_generator.py   # PDF + DOCX with screenshots
    │   ├── api/v1/
    │   │   ├── analysis.py       # Upload, status, results, reports
    │   │   ├── categories.py     # Category CRUD
    │   │   └── dashboard.py      # Stats + recent analyses
    │   ├── core/
    │   │   ├── config.py         # Pydantic settings
    │   │   └── seeder.py         # DB seeding (25 categories)
    │   ├── models/
    │   │   └── models.py         # SQLAlchemy ORM models
    │   └── schemas/
    │       └── schemas.py        # Pydantic request/response schemas
    │
    ├── skyrecon_visdrone.pt       # Fine-tuned: aerial people + vehicles
    ├── skyrecon_rdd2022.pt        # Fine-tuned: road damage + potholes
    ├── skyrecon_fire_smoke.pt     # Fine-tuned: fire & smoke
    ├── skyrecon_flood.pt          # Fine-tuned: flood water
    ├── skyrecon_trees_plants.pt   # Fine-tuned: trees & plants
    ├── yolov8s.pt                 # General COCO model (recommended)
    ├── yolov8n.pt                 # Fast COCO model
    └── yolov8x.pt                 # High-accuracy COCO model
```

---

## Getting Started

### Prerequisites
- Node.js >= 18
- Python >= 3.10
- PostgreSQL >= 14

### 1. Frontend
```bash
cd SkyRecon
npm install
npm run dev
# http://localhost:3000 — proxies /api/* to localhost:8000
```

### 2. Backend
```bash
cd SkyRecon/backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your PostgreSQL credentials
uvicorn app.main:app --reload --port 8000
```

On first startup: auto-creates DB, tables, stored procedures, seeds 25 categories.

SegFormer-B2 (~300MB) downloads automatically from HuggingFace on first tree/building/water detection.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `skyrecon` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| `YOLO_MODEL` | `yolov8s.pt` | Base fallback model |
| `CONFIDENCE_THRESHOLD` | `0.35` | Fallback confidence threshold |

---

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | API status + GPU info |
| `POST` | `/api/v1/analysis/upload` | Upload video/image, start AI |
| `GET` | `/api/v1/analysis/{id}/status` | Poll real progress % |
| `GET` | `/api/v1/analysis/{id}/summary` | Full results + coverage stats |
| `GET` | `/api/v1/analysis/{id}/detections` | Detection list with filters |
| `GET` | `/api/v1/analysis/{id}/disasters` | Disaster events for analysis |
| `POST` | `/api/v1/analysis/{id}/report` | Generate PDF or DOCX |
| `GET` | `/api/v1/analysis/report/{id}/status` | Poll report generation status |
| `GET` | `/api/v1/analysis/report/{id}/download` | Download report |
| `GET` | `/api/v1/analysis/reports/` | List all reports |
| `GET` | `/api/v1/analysis/` | List all analyses |
| `GET` | `/api/v1/analysis/{id}` | Get single analysis |
| `DELETE` | `/api/v1/analysis/{id}` | Delete analysis (cascade) |
| `GET` | `/api/v1/categories/` | List all 25 categories |
| `POST` | `/api/v1/categories/` | Create category |
| `PUT` | `/api/v1/categories/{id}` | Update category |
| `DELETE` | `/api/v1/categories/{id}` | Delete category |
| `GET` | `/api/v1/dashboard/stats` | Platform statistics |
| `GET` | `/api/v1/dashboard/recent` | Recent analyses |
| `GET` | `/api/v1/dashboard/map-markers` | GIS map markers |

Interactive docs: `http://localhost:8000/api/docs`

---

## Detection Categories (25)

| Category | Model | Method |
|---|---|---|
| People | `skyrecon_visdrone.pt` | YOLOv8 + ByteTrack |
| Vehicles | `skyrecon_visdrone.pt` | YOLOv8 + ByteTrack + char filter |
| Animals | `skyrecon_visdrone.pt` | YOLOv8 + ByteTrack |
| Road Potholes | `skyrecon_rdd2022.pt` | YOLOv8 + dark blob heuristic |
| Fire & Smoke | `skyrecon_fire_smoke.pt` | YOLOv8 + HSV mask |
| Flood Water | `skyrecon_flood.pt` | YOLOv8 + SegFormer + HSV |
| Trees | `skyrecon_trees_plants.pt` | SegFormer-B2 + ExG index |
| Plants | `skyrecon_trees_plants.pt` | SegFormer-B2 + HSV green |
| Water Bodies | `yolov8s.pt` | SegFormer-B2 + HSV blue |
| Buildings | `yolov8s.pt` | SegFormer-B2 + solidity |
| Houses | `yolov8s.pt` | SegFormer-B2 + solidity |
| Roads | `yolov8s.pt` | HSV asphalt + elongation |
| Electric Poles | `yolov8s.pt` | Vertical edge detection |
| Street Lights | `yolov8s.pt` | Vertical edge detection |
| Solar Panels | `yolov8s.pt` | HSV dark-blue mask |
| Agricultural Land | `yolov8s.pt` | HSV green + brown |
| Construction Zones | `yolov8s.pt` | HSV earth + yellow |
| Parking Areas | `yolov8s.pt` | HSV asphalt + area |
| Bridges | `yolov8s.pt` | Elongated edge detection |
| Pipelines | `yolov8s.pt` | Elongated edge detection |
| Traffic Lights | `yolov8s.pt` | YOLOv8 COCO |
| Railway Tracks | `yolov8s.pt` | YOLOv8 COCO |
| Garbage Areas | `yolov8s.pt` | YOLOv8 COCO |
| Warehouses | `yolov8s.pt` | SegFormer-B2 + geometric |
| Shops | `yolov8s.pt` | SegFormer-B2 + geometric |

---

## Report Contents

Every PDF/DOCX report includes:
- Analysis context banner (category + active filters)
- Project info (name, location, drone model, date, processing time)
- Detection summary (unique count, area covered, coverage %)
- Category breakdown table
- Top detections by confidence with timestamps
- One cropped screenshot per unique object with timestamp + confidence
- AI planning recommendations

---

<p align="center">
  <b>SkyRecon</b> – <em>AI Powered Aerial Intelligence & Disaster Monitoring Platform</em><br/>
  Built with love at NIT Rourkela · 2026 Drone Internship
</p>
