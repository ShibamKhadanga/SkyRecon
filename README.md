<p align="center">
  <img src="public/skyrecon-favicon.svg" alt="SkyRecon Logo" width="80" />
</p>

<h1 align="center">SkyRecon – AI Powered Drone Intelligence Platform</h1>

<p align="center">
  <b>Smart Aerial Mapping • Disaster Detection & Response • Real-Time GIS Intelligence</b><br/>
  <em>Built for NIT Rourkela Drone Internship 2026</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React%2019%20+%20Vite-61DAFB?style=flat-square&logo=react" />
  <img src="https://img.shields.io/badge/Backend-FastAPI%200.115-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/AI-YOLOv8s%20+%20ByteTrack-FF6F00?style=flat-square" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL-4169E1?style=flat-square&logo=postgresql" />
  <img src="https://img.shields.io/badge/Maps-Leaflet%20GIS-199900?style=flat-square&logo=leaflet" />
  <img src="https://img.shields.io/badge/Weather-Open--Meteo-00BFFF?style=flat-square" />
  <img src="https://img.shields.io/badge/Air%20Traffic-OpenSky%20Network-1E90FF?style=flat-square" />
  <img src="https://img.shields.io/badge/Satellites-Celestrak-9B59B6?style=flat-square" />
</p>

---

## What is SkyRecon?

SkyRecon is a full-stack AI drone intelligence platform that processes real drone video using **YOLOv8s + ByteTrack + OpenCV**. Upload a drone video, select what you want to detect, and the platform runs real computer vision inference frame by frame — giving you accurate unique object counts, area coverage in m², annotated screenshots, and downloadable PDF/DOCX reports.

The GIS map page goes beyond just showing detection markers — it integrates **live weather overlays**, **real-time air traffic** from OpenSky Network, and **live satellite tracking** from Celestrak, all using free APIs with no API keys required.

---

## Two Core Modules

**Mapping & Survey** — Detect and count unique objects from 25 categories (vehicles, people, buildings, potholes, poles, trees, and more) from aerial footage. Uses ByteTrack persistent object tracking to count each unique object only once across the entire video, regardless of how many frames it appears in.

**Disaster Response** — Scan footage for fire, flood, structural damage, fallen poles, and more. Each confirmed event gets a severity score (1–5), a screenshot from the best detection frame, auto-calculated rescue resource estimates, and an actionable recommendations report.

---

## Tech Stack

### Frontend
| Library | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| Vite | 6 | Build tool & dev server |
| TailwindCSS | 4 | Utility-first styling |
| Framer Motion | 12 | Animations & page transitions |
| React Router DOM | 7 | Client-side routing |
| Recharts | 3 | Dashboard area/pie/bar charts |
| Leaflet + React-Leaflet | 5 | Interactive GIS map |
| Lucide React | latest | Icon library |

### Backend
| Library | Version | Purpose |
|---|---|---|
| FastAPI | 0.115 | REST API framework |
| Uvicorn | 0.30 | ASGI server |
| httpx | 0.27 | Async HTTP client — OpenSky & Celestrak proxy |
| SQLAlchemy | 2.0 | ORM |
| PostgreSQL + psycopg2 | — | Database (6 tables, 12 stored procedures) |
| Ultralytics YOLOv8s | ≥8.3 | Object detection + ByteTrack tracking |
| OpenCV (headless) | ≥4.10 | Video frame extraction & CLAHE enhancement |
| PyTorch | ≥2.3 | Deep learning runtime |
| NumPy | ≥1.26 | Array/matrix operations |
| ReportLab | 4.2 | PDF report generation |
| python-docx | 1.1 | DOCX report generation |
| Pillow | 11.0 | Screenshot processing |

### External Free APIs (no keys required)
| API | Purpose |
|---|---|
| [Open-Meteo](https://open-meteo.com/) | Real-time weather — temperature, humidity, wind, pressure |
| [OpenSky Network](https://opensky-network.org/) | Live aircraft positions (anonymous: ~400 req/day) |
| [Celestrak](https://celestrak.org/) | Satellite TLE orbital data — visual satellites group |
| [OpenTopoMap](https://opentopomap.org/) | Terrain tile layer with elevation contours |

---

## Project Structure

```
SkyRecon/
├── src/                              # React frontend
│   ├── layouts/
│   │   └── AppLayout.jsx             # Sidebar + navbar + breadcrumbs
│   ├── components/ui/                # Reusable UI components
│   │   ├── StatCard.jsx              # Animated stat card with trend
│   │   ├── GlassCard.jsx             # Glassmorphism card wrapper
│   │   ├── NeonButton.jsx            # 5-variant button with glow/ripple
│   │   ├── AnimatedCounter.jsx       # Spring-animated number counter
│   │   ├── RadarPulse.jsx            # Rotating radar sweep animation
│   │   ├── SeverityBadge.jsx         # 5-level color-coded severity
│   │   ├── ConfidenceBar.jsx         # AI confidence progress bar
│   │   ├── FileDropzone.jsx          # Drag-drop video upload zone
│   │   └── LoadingScreen.jsx         # Full-screen radar loading
│   └── pages/
│       ├── LandingPage.jsx           # Module selection hub with animations
│       ├── DashboardPage.jsx         # Command center — charts, stats, banners
│       ├── MappingPage.jsx           # AI mapping workspace
│       ├── DisasterPage.jsx          # Disaster scan workspace
│       ├── MapPage.jsx               # GIS map — weather, air traffic, satellites
│       ├── ReportsPage.jsx           # Report browser + download
│       └── AdminPage.jsx             # Admin panel — categories, AI settings
│
└── backend/
    ├── requirements.txt              # All Python dependencies (annotated)
    ├── .env                          # Environment config (create from .env.example)
    ├── .env.example                  # Config template
    ├── yolov8s.pt                    # YOLOv8s model weights (auto-downloaded)
    ├── sql/
    │   └── procedures.sql            # 12 PL/pgSQL stored procedures
    └── app/
        ├── main.py                   # FastAPI app entry point
        ├── database.py               # DB engine, session, auto-init
        ├── ai/
        │   ├── video_processor.py    # Core AI pipeline (YOLOv8 + ByteTrack)
        │   ├── disaster_engine.py    # Disaster classification + severity scoring
        │   ├── area_calculator.py    # Bounding box → real-world m² conversion
        │   └── report_generator.py  # PDF + DOCX report builder
        ├── api/v1/
        │   ├── analysis.py           # Upload, background tasks, results, reports
        │   ├── categories.py         # Category CRUD
        │   └── dashboard.py          # Stats, map markers, weather proxy, air traffic, satellites
        ├── core/
        │   └── config.py             # Settings from .env
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
# → http://localhost:3000
```

> On first backend startup, it automatically creates the `skyrecon` database, all 6 tables, installs all 12 stored procedures, seeds the 25 detection categories, and populates sample data if the DB is empty.

> YOLOv8s model weights (`yolov8s.pt`, ~22MB) download automatically on the first analysis run.

---

## GIS Map Features

The map page (`/map`) is the most feature-rich page in the platform.

### Map Layers
| Layer | Source | Best For |
|---|---|---|
| 🏔️ Terrain | OpenTopoMap | Default — elevation contours, rivers, forests. Best for drone recon |
| 🛰️ Satellite | ArcGIS World Imagery | Visual ground truth |
| 🗺️ Streets | OpenStreetMap | Road network & city layout |

### Live Weather Overlays
Powered by **Open-Meteo** (free, no API key). Fetched automatically when GPS is granted.

- Current conditions: temperature, feels-like, humidity, wind speed, weather description
- **Map overlay modes** (toggle in sidebar):
  - 🌡️ **Temperature** — color-coded circles: blue (cold) → green (mild) → orange (hot) → red (very hot)
  - 🔵 **Pressure** — blue (low pressure / storm risk) → cyan (normal ~1013 hPa) → orange (high pressure)
  - 💨 **Wind** — green (calm) → yellow (moderate) → red (strong winds)
- Overlays are rendered as a 4×4 grid of 16 surrounding points — click any circle for exact value + coordinates

### Live Air Traffic
Powered by **OpenSky Network** (free, anonymous access).

- Toggle **✈️ Air Traffic** in the sidebar to fetch all aircraft currently flying within ~900km of your location
- Each aircraft shown as a rotated ✈️ emoji pointing in its heading direction
- Click any aircraft for: callsign, country, altitude (m), speed (m/s), heading, airborne/ground status
- Anonymous limit: ~400 requests/day. Register free at opensky-network.org for 4000/day

### Live Satellite Tracking
Powered by **Celestrak** (free, no API key).

- Toggle **🛰️ Satellites** to load the 50 brightest visible satellites
- Positions computed from TLE orbital elements using mean motion propagation
- Click any satellite for: name, altitude (km), orbital inclination, orbital period (minutes)

### Recon Site Markers
- Only shows **real detection markers** from your database (`gps_lat`/`gps_lon` on detections and disaster events)
- No hardcoded mock data — shows a clean empty state until you run an analysis
- Heatmap toggle scales circle radius by detection count

---

## Dashboard Features

### Banners
- **Welcome banner** — shown on first visit when no analyses exist. Links directly to Mapping and Disaster workspaces. Dismissed permanently via localStorage
- **Offline banner** — shown when the FastAPI backend is unreachable. Dismissible per-session. Auto-hides when backend comes back online

### Charts
- **Analysis Trend** — area chart of detections + analyses by day of week (rolling 7-day window, today last)
- **Detection Categories** — donut pie chart of real category breakdown from completed analyses
- **Recent Analyses** — clickable list, navigates to the correct workspace per analysis mode
- **Quick Actions** — one-click navigation to all major platform sections

---

## How the AI Pipeline Works

### Mapping Analysis

```
User uploads drone video + selects category (e.g. People)
        ↓
FastAPI saves file → creates DB record → launches BackgroundTask
        ↓
video_processor.py:
  1. OpenCV opens video
  2. Seek-based frame extraction: cap.set(CAP_PROP_POS_FRAMES, idx)
     → Only target frames are decoded — skipped frames cost zero CPU
  3. Adaptive CLAHE contrast enhancement:
     → Checks grayscale std deviation first
     → If std > 45 (already high contrast), skips enhancement entirely
  4. Frame resized to 640px width for faster YOLOv8 inference
  5. YOLOv8s + ByteTrack runs inference → detections filtered to selected category
  6. ByteTrack assigns each unique object a persistent track_id across the video
     - Same person walking across 50 frames = 1 track_id = counted once
     - 3 different people = 3 track_ids = counted as 3
  7. Only first-appearance detections saved to DB (no duplicate rows)
  8. Annotated screenshots saved at detection frames (max 8 per analysis)
  9. Progress written to progress_pct column every 5% → frontend polls every 3s
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
  1. Seek-based frame extraction (same as mapping)
  2. Classifies 7 disaster types: fire, flood, structural, people, vehicles, trees, poles
  3. Must appear in ≥ 3 sampled frames to be confirmed (eliminates noise)
  4. Severity 1–5 computed from:
       base weight (fire=5, flood=4, structural=3, others=1)
       + density bonus + area ratio bonus + confidence factor
  5. Best screenshot saved per confirmed disaster type
  6. Resource estimation auto-calculated (rescue teams, ambulances, boats, staff)
        ↓
Frontend shows confirmed events with screenshots + severity distribution strip
Voice alert fires ONLY for fire or flood at severity ≥ 4
PDF/DOCX report downloadable
```

---

## API Reference

Base URL: `http://localhost:8000`
Interactive docs: `http://localhost:8000/api/docs`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | API status + GPU availability |
| `POST` | `/api/v1/analysis/upload` | Upload video, start AI pipeline |
| `GET` | `/api/v1/analysis/{id}/status` | Poll processing progress (0–100%) |
| `GET` | `/api/v1/analysis/{id}/summary` | Full results — counts, coverage, breakdown |
| `GET` | `/api/v1/analysis/{id}/detections` | All unique detections (filterable by category) |
| `GET` | `/api/v1/analysis/{id}/disasters` | All confirmed disaster events |
| `POST` | `/api/v1/analysis/{id}/report` | Generate PDF or DOCX report |
| `GET` | `/api/v1/analysis/report/{id}/status` | Report generation status |
| `GET` | `/api/v1/analysis/report/{id}/download` | Download generated report file |
| `GET` | `/api/v1/analysis/reports/` | List all completed analyses |
| `DELETE` | `/api/v1/analysis/{id}` | Delete analysis + all related data |
| `GET` | `/api/v1/categories/` | List all 25 detection categories |
| `GET` | `/api/v1/dashboard/stats` | Platform-wide statistics |
| `GET` | `/api/v1/dashboard/recent-analyses` | Recent analysis jobs |
| `GET` | `/api/v1/dashboard/map-markers` | Live GIS markers from DB (no mock data) |
| `GET` | `/api/v1/dashboard/live-aircraft` | **Live aircraft** via OpenSky Network proxy |
| `GET` | `/api/v1/dashboard/live-satellites` | **Live satellites** via Celestrak TLE proxy |

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

## Detection Categories (25)

| Category | Detection Method |
|---|---|
| Vehicles | car, truck, bus, motorcycle, bicycle, boat, airplane |
| People | person + accessories |
| Plants | potted plant |
| Trees | vegetation context |
| Electric Poles | tall narrow aspect ratio heuristic (h/w > 3.5) |
| Traffic Lights | traffic light class |
| Roads | road surface context |
| Road Potholes | road surface analysis |
| Water Bodies | boat context + flood detection |
| Buildings | indoor object context |
| Houses | bed, couch context |
| Parking Areas | vehicle density analysis |
| Garbage Areas | bottle, cup, wine glass |
| Construction Zones | site context |
| Agricultural Land | crop field context |
| Animals | cat, dog, horse, cow, sheep, bird, elephant, bear, zebra, giraffe |
| Solar Panels | rooftop context |
| Bridges | structural context |
| Railway Tracks | train class |
| Fire & Smoke | fire/flame triggers |
| Flood Water | boat + water accumulation |
| Shops | commercial context |
| Warehouses | industrial context |
| Pipelines | pipeline context |
| Street Lights | tall narrow aspect ratio heuristic |

---

## Choosing a YOLO Model

| Model | Size | Speed | Accuracy | Recommended For |
|---|---|---|---|---|
| `yolov8n.pt` | 6 MB | Fastest | Lower | Development / testing only |
| `yolov8s.pt` | 22 MB | Fast | Good | **Default — balanced CPU performance** |
| `yolov8m.pt` | 52 MB | Medium | Better | GPU machines, production use |

Set `YOLO_MODEL=yolov8s.pt` in `.env`. The model downloads automatically on first use.

---

## Known Limitations

- YOLOv8 is trained on COCO (80 classes). Categories like potholes, solar panels, and agricultural land are approximated through class mapping and heuristics.
- CPU processing: ~1–2 minutes per minute of 1080p video at 1fps sampling. GPU (CUDA) is ~5–10× faster.
- OpenSky anonymous access allows ~400 requests/day. Register free at opensky-network.org for 4000/day.
- Satellite positions are computed from TLE mean motion approximation — accurate enough for map display but not precise orbital mechanics.
- The GIS map shows no markers until at least one analysis with GPS coordinates is completed.
- Weather overlays require GPS permission to be granted in the browser.

---

<p align="center">
  <b>SkyRecon</b> – <em>AI Powered Aerial Intelligence & Disaster Monitoring Platform</em><br/>
  Built with ❤️ at NIT Rourkela · 2026 Drone Internship
</p>
