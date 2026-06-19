<p align="center">
  <img src="public/skyrecon-favicon.svg" alt="SkyRecon Logo" width="80" />
</p>

<h1 align="center">SkyRecon – AI Powered Drone Intelligence Platform</h1>

<p align="center">
  <b>Smart Aerial Mapping • Disaster Detection & Response • Real-Time Drone Analytics</b><br/>
  <em>Built for NIT Rourkela Drone Internship 2026</em><br/>
  <em>By: <strong>S. Khadanga</strong></em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Frontend-React%2019%20+%20Vite%205-61DAFB?style=flat-square&logo=react" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi" />
  <img src="https://img.shields.io/badge/AI-YOLOv8%20+%20CLIP%20+%20ByteTrack-FF6F00?style=flat-square" />
  <img src="https://img.shields.io/badge/Database-PostgreSQL%20%7C%20Neon-4169E1?style=flat-square&logo=postgresql" />
  <img src="https://img.shields.io/badge/Maps-Leaflet%20GIS-199900?style=flat-square&logo=leaflet" />
  <img src="https://img.shields.io/badge/Segmentation-SegFormer--B2-764ABC?style=flat-square" />
  <img src="https://img.shields.io/badge/Face%20Detection-OpenCV%20Haar-5C3EE8?style=flat-square&logo=opencv" />
  <img src="https://img.shields.io/badge/Mobile-PWA%20Ready-5A0FC8?style=flat-square&logo=pwa" />
  <img src="https://img.shields.io/badge/Backend-HuggingFace%20Spaces-FFD21E?style=flat-square&logo=huggingface" />
  <img src="https://img.shields.io/badge/Frontend-Vercel-000000?style=flat-square&logo=vercel" />
</p>

---

## 🌐 Live Deployment

| Service | URL | Platform |
|---|---|---|
| **Frontend** | [skyrecon.vercel.app](https://skyrecon.vercel.app) | Vercel |
| **Backend API** | [shibamkhadanga-skyrecon.hf.space](https://shibamkhadanga-skyrecon.hf.space) | HuggingFace Spaces |
| **API Health** | [/api/health](https://shibamkhadanga-skyrecon.hf.space/api/health) | — |
| **API Docs** | [/api/docs](https://shibamkhadanga-skyrecon.hf.space/api/docs) | — |
| **Database** | Neon PostgreSQL | neon.tech |
| **GitHub Repo** | [ShibamKhadanga/SkyRecon](https://github.com/ShibamKhadanga/SkyRecon) | GitHub |
| **Model Weights** | [Releases → v1.0-models](https://github.com/ShibamKhadanga/SkyRecon/releases/tag/v1.0-models) | GitHub Releases |

---

## What is SkyRecon?

SkyRecon is a full-stack AI drone intelligence platform that **actually processes drone video** using a multi-model AI pipeline. Upload a drone video or image, select what you want to detect, and the platform runs real computer vision inference frame by frame and gives you a detailed report with real counts, area coverage, and per-object screenshots.

### Core Modules

| Module | Description |
|---|---|
| **Mapping & Survey** | Detect 25 categories from aerial footage using specialized fine-tuned models. Get real unique object counts via ByteTrack + CLIP visual deduplication + per-frame floor enforcement, area coverage in m², full-frame annotated screenshots with bounding boxes, and downloadable PDF/DOCX reports with sort (name/date/objects). |
| **Disaster Response** | Scan footage for floods, fire, structural damage, fallen poles. Each event gets severity 1–5, a screenshot from the exact video frame, resource estimates, and an actionable report. |
| **Live Drone Feed** | Real-time video streaming with telemetry HUD overlay, in-browser recording, and multi-protocol support (FPV USB receiver, MJPEG, HLS, Direct MP4). |
| **Object Finder** | Two search modes: **Facial Attributes** (filter by gender, age, hair, glasses, skin tone, clothing) and **Visual Match** (face-level CLIP matching with OpenCV Haar face detection). Scans uploaded video or live stream and returns every appearance with timestamp, confidence, full-frame thumbnail, and PDF export. |

---

## AI Models

SkyRecon uses 7 specialized fine-tuned models alongside base YOLOv8:

| Model File | Trained On | Best For |
|---|---|---|
| `skyrecon_visdrone.pt` | VisDrone2019 | People & vehicles from aerial view |
| `skyrecon_rdd2022.pt` | RDD2022 Road Damage | Potholes, road cracks |
| `skyrecon_fire_smoke.pt` | Fire/Smoke dataset | Fire detection, smoke plumes |
| `skyrecon_flood.pt` | Flood imagery | Flood water, inundated areas |
| `skyrecon_trees_plants.pt` | Aerial vegetation | Trees & plants |
| `skyrecon_buildings.pt` | `keremberke/yolov8s-building-segmentation` (HF Hub) | Buildings & houses segmentation |
| `skyrecon_solar_panels.pt` | `finloop/yolov8s-seg-solar-panels` (HF Hub) | Solar panel detection |
| `yolov8s.pt` | COCO (general) | Recommended fallback |
| `yolov8n.pt` | COCO (general) | Fast fallback (free-tier servers) |
| `yolov8x.pt` | COCO (general) | High accuracy (requires GPU) |

The pipeline automatically selects the best model per category. On deployment, all models are downloaded at Docker build time from GitHub Releases via `download_models.py`.

---

## Detection Pipeline

### YOLO-Detectable Categories (People, Vehicles, Animals...)

```
Frame → CLAHE Enhancement → Resize 960px → YOLOv8 + ByteTrack
     → Aerial misclassification fix (kite→person etc.)
     → Characteristics filter (2-Wheeler, color, etc.)
     → Per-frame object counting (tracks max per-frame as floor)
     → Unique object tracking (one count per track ID)
     → Full-frame annotated screenshot per detection
     → CLIP visual deduplication (post-processing, threshold 0.88)
     → Per-frame floor enforcement (prevents CLIP from under-counting)
     → DB pruning (delete duplicate detection records)
```

### Aerial-Specific Categories (Trees, Water, Buildings, Roads, Fire...)

```
Frame → SegFormer-B2 segmentation + OpenCV heuristics
     → ExG vegetation index (trees/plants)
     → HSV color analysis (fire, water, solar panels)
     → Edge detection (poles, bridges, pipelines)
     → Grid-based deduplication
```

### Object Finder Pipeline (Visual Match Mode)

```
Target Photo → OpenCV Haar face detection → Face crop + body crop
            → CLIP embedding (face + full image)

Video Frame → YOLO person detection → Person crop
           → OpenCV face detection within crop
           → CLIP face-to-face similarity (70% weight)
           → CLIP body-to-body similarity (30% weight)
           → CLIP dedup across matches (same person = keep best)
           → Top 20 matches sorted by confidence
```

---

## Libraries Used

### Frontend (JavaScript / React)

| Library | Version | Purpose |
|---|---|---|
| **React** | 19.1 | UI framework — component-based rendering |
| **React DOM** | 19.1 | DOM rendering for React components |
| **Vite** | 5.4 | Build tool — HMR, fast dev server, production bundler |
| **React Router DOM** | 7.15 | Client-side routing (10 pages) |
| **TailwindCSS** | 4.3 | Utility-first CSS framework for styling |
| **@tailwindcss/vite** | 4.3 | Vite-native TailwindCSS plugin |
| **@vitejs/plugin-react** | 4.3 | React Fast Refresh + JSX transform for Vite |
| **Framer Motion** | 12.40 | Animation library — page transitions, micro-animations |
| **Leaflet** | 1.9 | Interactive GIS maps with markers and heatmaps |
| **React-Leaflet** | 5.0 | React wrapper for Leaflet maps |
| **Recharts** | 3.8 | Chart library (bar, line, pie charts for dashboard) |
| **Lucide React** | 1.17 | Icon library (consistent SVG icons) |
| **TypeScript** | 6.0 | Static type checking |

### Backend (Python / FastAPI)

| Library | Version | Purpose |
|---|---|---|
| **FastAPI** | ≥0.115 | REST API framework — async, auto-docs (Swagger/OpenAPI) |
| **Uvicorn** | ≥0.30 | ASGI server — serves FastAPI with auto-reload |
| **SQLAlchemy** | ≥2.0 | ORM + raw SQL — PostgreSQL database access |
| **psycopg2-binary** | ≥2.9 | PostgreSQL adapter (binary wheel, no build tools) |
| **Pydantic** | ≥2.9 | Data validation — request/response schemas |
| **Pydantic Settings** | ≥2.5 | Environment variable management via `.env` |
| **python-multipart** | ≥0.0.12 | File upload parsing for FastAPI endpoints |
| **aiofiles** | ≥24.1 | Async file I/O for uploads |
| **httpx** | ≥0.27 | Async HTTP client — SSE stream proxy, camera stream relay |

### AI / Computer Vision (Python)

| Library | Version | Purpose |
|---|---|---|
| **PyTorch** | ≥2.3 | Deep learning runtime — tensor operations, GPU acceleration |
| **TorchVision** | ≥0.18 | Vision utilities — transforms, pretrained model support |
| **Ultralytics** | ≥8.3 | YOLOv8 object detection + ByteTrack multi-object tracking |
| **OpenCV** (headless) | ≥4.10 | Frame extraction, Haar cascade face detection, CLAHE enhancement, HSV color analysis, edge detection, contour detection, image annotation |
| **Transformers** (HuggingFace) | ≥4.40 | SegFormer-B2 (aerial segmentation) + CLIP `openai/clip-vit-base-patch32` (object finder visual matching + mapping visual dedup) |
| **Accelerate** | ≥0.30 | HuggingFace GPU inference support for SegFormer |
| **Pillow** | ≥10.0 | Image processing — format conversion, thumbnail generation |
| **NumPy** | ≥1.26 | Numerical arrays — image manipulation, similarity computation |

### Report Generation (Python)

| Library | Version | Purpose |
|---|---|---|
| **ReportLab** | ≥4.2 | PDF report generation with screenshots and tables |
| **python-docx** | ≥1.1 | DOCX (Word) report generation |
| **Jinja2** | ≥3.1 | Template engine for report formatting |

### Infrastructure / DevOps

| Library / Service | Purpose |
|---|---|
| **Docker** | Container for HuggingFace Spaces deployment |
| **python-dotenv** | Load `.env` files for local development |
| **Vercel** | Frontend static hosting (free tier) |
| **HuggingFace Spaces** | Backend Docker hosting (free CPU / paid GPU) |
| **Neon** | Serverless PostgreSQL database (free 512 MB) |
| **GitHub Releases** | Model weight hosting (up to 2 GB/file) |

### Key AI Techniques Used

| Technique | Where Used | Description |
|---|---|---|
| **YOLOv8 Object Detection** | Mapping, Disaster, Find Object | Real-time object detection across 80 COCO classes + 7 custom-trained models |
| **ByteTrack** | Mapping | Multi-object tracking — assigns persistent IDs across video frames |
| **CLIP Visual Matching** | Object Finder, Mapping Dedup | Cosine similarity between image embeddings for person re-identification |
| **CLIP Face-to-Face** | Object Finder | OpenCV Haar cascade detects faces → CLIP compares face crops (not full-body) for higher accuracy |
| **CLIP Visual Dedup** | Mapping | Post-processing: pairwise CLIP comparison of all person crops, merging duplicates (sim > 0.88) with same-frame protection |
| **Per-Frame Floor** | Mapping | Tracks the maximum number of objects detected in any single frame — guarantees final count ≥ this floor, preventing CLIP from over-merging |
| **SegFormer-B2** | Trees, Water, Buildings | Semantic segmentation — pixel-level classification of aerial imagery |
| **CLAHE Enhancement** | All Detection | Contrast-limited adaptive histogram equalization — improves detection in shadowed/overexposed frames |
| **ExG Vegetation Index** | Trees, Plants | `ExG = 2*G - R - B` — isolates green vegetation from aerial RGB |
| **HSV Color Analysis** | Fire, Water, Roads, Solar | Hue-Saturation-Value masking for material/surface classification |
| **Haar Cascade Face Detection** | Object Finder | OpenCV's built-in frontal face detector — extracts face crops from target photos and person detections |
| **DB Pruning** | Mapping | After CLIP dedup, excess detection records are deleted from PostgreSQL — keeps only top N by confidence |

---

## Tech Stack

### Frontend
| | |
|---|---|
| React 19 + Vite 5 | UI + build |
| TailwindCSS 4 + @tailwindcss/vite | Styling (Vite-native plugin) |
| Framer Motion 12 | Animations |
| React Router DOM 7 | Routing |
| Recharts 3 | Charts |
| Leaflet 1.9 + React-Leaflet 5 | GIS map |
| Lucide React | Icons |
| TypeScript 6 | Type checking |

### Backend
| | |
|---|---|
| FastAPI | REST API |
| SQLAlchemy 2.0 + PostgreSQL (Neon) | Database |
| Ultralytics YOLOv8 | Detection + ByteTrack tracking |
| OpenCV | Frame extraction + face detection + heuristic detection |
| PyTorch | Deep learning runtime |
| SegFormer-B2 (HuggingFace) | Aerial semantic segmentation |
| CLIP `openai/clip-vit-base-patch32` | Object Finder face matching + Mapping visual dedup |
| OpenCV Haar Cascade | Face detection (target photo + person crops) |
| ReportLab + python-docx | PDF + DOCX report generation |
| Docker | Container for HuggingFace Spaces deployment |

### Infrastructure
| | |
|---|---|
| HuggingFace Spaces (Docker) | Backend hosting (free CPU/GPU) |
| Vercel | Frontend hosting (free static) |
| Neon | PostgreSQL database (free 512 MB) |
| GitHub Releases | Model weight hosting (up to 2 GB/file) |

---

## Project Structure

```
SkyRecon/
├── index.html                        # Entry HTML
├── package.json                      # Frontend dependencies
├── vite.config.js                    # Vite bundler + proxy config
├── tsconfig.json                     # TypeScript configuration
├── vercel.json                       # Vercel deploy config (rewrites → HF Space)
├── render.yaml                       # Render.com IaC blueprint (alternative backend)
│
├── src/                              # React frontend source
│   ├── main.jsx                      # App entry point
│   ├── App.jsx                       # Routes (10 pages)
│   ├── index.css                     # Global styles + Tailwind
│   ├── layouts/
│   │   └── AppLayout.jsx             # Sidebar + navbar (mobile responsive)
│   ├── hooks/
│   │   ├── useWeather.js             # Open-Meteo weather + drone safety check
│   │   └── useRecordingsStore.js     # localStorage recordings store + cross-tab sync
│   ├── lib/
│   │   └── api.js                    # fetchJson utility (API base URL + error handling)
│   ├── components/
│   │   ├── Sidebar.jsx               # Navigation sidebar
│   │   └── ui/                       # Reusable UI components
│   │       ├── AnimatedCounter.jsx
│   │       ├── ConfidenceBar.jsx
│   │       ├── FileDropzone.jsx
│   │       ├── GlassCard.jsx
│   │       ├── NeonButton.jsx
│   │       ├── RadarPulse.jsx
│   │       ├── SeverityBadge.jsx
│   │       ├── StatCard.jsx
│   │       └── WeatherBar.jsx        # Live weather strip + unsafe-to-fly warning banner
│   └── pages/
│       ├── LandingPage.jsx           # Module selection landing
│       ├── DashboardPage.jsx         # Statistics dashboard
│       ├── MappingPage.jsx           # Upload + config + results (mapping)
│       ├── DisasterPage.jsx          # Upload + config + results (disaster)
│       ├── MapPage.jsx               # GIS map with markers + heatmaps
│       ├── ReportsPage.jsx           # Report listing + download + sort (name/date/objects)
│       ├── AdminPage.jsx             # Category & system management
│       ├── LiveFeedPage.jsx          # Real-time drone stream + telemetry + recording
│       ├── RecordingsPage.jsx        # Playback, download & manage + sort (name/date/size/duration)
│       └── FindPage.jsx              # AI object finder (face matching + CLIP visual match + PDF export)
│
├── public/
│   └── skyrecon-favicon.svg          # App favicon
│
└── backend/                          # FastAPI backend (deployed to HuggingFace Spaces)
    ├── Dockerfile                    # Docker image for HuggingFace Spaces (port 7860)
    ├── Procfile                      # Render.com process definition
    ├── requirements.txt              # Python dependencies
    ├── download_models.py            # Downloads .pt weights from GitHub Releases at build time
    ├── download_hf_models.py         # Downloads buildings + solar panels models from HuggingFace Hub
    ├── optimize_models.py            # Strips optimizer state + EMA promotion + FP16 conversion
    ├── .env.example                  # Environment variable template
    │
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                   # FastAPI app + CORS + routes
    │   ├── database.py               # SQLAlchemy engine + DB init
    │   ├── ai/
    │   │   ├── video_processor.py    # Full mapping pipeline (YOLO + ByteTrack + SegFormer + CLIP dedup)
    │   │   ├── disaster_engine.py    # Disaster classification + severity scoring
    │   │   ├── area_calculator.py    # Bounding box → real-world m²
    │   │   ├── face_finder.py        # Facial attribute search (YOLO person + CLIP matching)
    │   │   └── report_generator.py   # PDF + DOCX with screenshots
    │   ├── api/v1/
    │   │   ├── analysis.py           # Upload, status, results, reports, object finder (face-level CLIP)
    │   │   ├── categories.py         # Category CRUD
    │   │   ├── dashboard.py          # Stats + recent analyses + map markers
    │   │   └── stream.py             # SSE real-time progress streaming
    │   ├── core/
    │   │   ├── config.py             # Pydantic settings
    │   │   └── seeder.py             # DB seeding (25 categories)
    │   ├── models/
    │   │   └── models.py             # SQLAlchemy ORM models
    │   └── schemas/
    │       └── schemas.py            # Pydantic request/response schemas
    │
    ├── sql/
    │   └── procedures.sql            # 12 PL/pgSQL stored procedures
    │
    ├── uploads/                      # Uploaded video/image files (runtime)
    ├── screenshots/                  # Full-frame annotated screenshots (runtime)
    ├── reports/                      # Generated PDF/DOCX reports (runtime)
    │
    ├── SkyRecon_VisDrone_Training.ipynb      # Training notebook: VisDrone people & vehicles
    ├── SkyRecon_FireSmoke_Training.ipynb     # Training notebook: fire & smoke detection
    ├── SkyRecon_Flood_Training.ipynb         # Training notebook: flood water detection
    ├── SkyRecon_RDD2022_RoadDamage.ipynb     # Training notebook: road damage & potholes
    ├── SkyRecon_Buildings_Training.ipynb     # Training notebook: building segmentation
    ├── SkyRecon_TreesPlants_Training.ipynb   # Training notebook: vegetation detection
    │
    ├── visdrone_download.py          # Script to download VisDrone dataset
    ├── visdrone_convert.py           # Script to convert VisDrone annotations to YOLO format
    ├── visdrone_train.py             # Script to run VisDrone training
    │
    ├── skyrecon_visdrone.pt          # Fine-tuned: aerial people + vehicles (136 MB)
    ├── skyrecon_rdd2022.pt           # Fine-tuned: road damage + potholes (22 MB)
    ├── skyrecon_fire_smoke.pt        # Fine-tuned: fire & smoke (545 MB)
    ├── skyrecon_flood.pt             # Fine-tuned: flood water (136 MB)
    ├── skyrecon_trees_plants.pt      # Fine-tuned: trees & plants (89 MB)
    ├── skyrecon_buildings.pt         # HuggingFace Hub: keremberke/yolov8s-building-segmentation
    ├── skyrecon_solar_panels.pt      # HuggingFace Hub: finloop/yolov8s-seg-solar-panels
    ├── yolov8s.pt                    # General COCO model (recommended)
    ├── yolov8n.pt                    # Fast COCO model (free-tier safe)
    └── yolov8x.pt                    # High-accuracy COCO model (GPU only)
```

> **Note:** `.pt` model files are excluded from Git (`.gitignore`). They are hosted on [GitHub Releases → v1.0-models](https://github.com/ShibamKhadanga/SkyRecon/releases/tag/v1.0-models) and downloaded automatically at Docker build time via `download_models.py`.

---

## Getting Started (Local)

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

On first startup: auto-creates DB tables, runs stored procedures, seeds 25 categories.

SegFormer-B2 (~300 MB) downloads automatically from HuggingFace on first tree/building/water detection.

CLIP model (`openai/clip-vit-base-patch32` ~600 MB) downloads automatically on first Object Finder or Mapping analysis with visual dedup.

> Tip: For GPU inference with SegFormer, install `accelerate` via `pip install accelerate`.

---

## 🚀 Deployment (Actual Deployed Architecture)

```
GitHub Repo (ShibamKhadanga/SkyRecon)
  |-- Frontend (React/Vite)   --> Vercel          --> https://skyrecon.vercel.app  [FREE]
  |-- Backend  (FastAPI+YOLO) --> HF Spaces       --> https://shibamkhadanga-skyrecon.hf.space [FREE]
                                       |
                                  Neon PostgreSQL                                              [FREE]
```

> Vercel's `vercel.json` proxies all `/api/*`, `/uploads/*`, `/screenshots/*`, `/reports/*` requests directly to the HuggingFace Space — no CORS issues, single domain for the frontend.

### Deployment Files

| File | Purpose |
|---|---|
| `vercel.json` | Vercel rewrites → HF Space, SPA fallback, security headers |
| `render.yaml` | Render.com IaC blueprint (alternative backend option) |
| `backend/Dockerfile` | Python 3.11 Docker image, runs on port 7860 for HF Spaces |
| `backend/Procfile` | Render.com start command |
| `backend/download_models.py` | Downloads all `.pt` weights from GitHub Releases at build time |

### Free Tier Performance

| Platform | RAM | All Custom Models? | Cost |
|---|---|---|---|
| **HuggingFace Spaces CPU Basic** | 16 GB | ✅ All models run | Free |
| Render Starter | 2 GB | ✅ yolov8s + custom | $7/month |
| Render Free | 512 MB | ❌ yolov8n only | Free |

| Model | Accuracy (mAP50) | On HF Spaces (deployed)? |
|---|---|---|
| `yolov8n.pt` | 37.3 — minimal | ✅ Runs |
| `yolov8s.pt` | 44.9 — good | ✅ Runs |
| `yolov8x.pt` | 53.9 — full | ✅ Runs (no GPU, slower) |
| Custom `.pt` models | Custom trained | ✅ All 7 run |

> **This deployment uses HuggingFace Spaces CPU Basic (2 vCPU · 16 GB RAM)** — all 5 custom fine-tuned models run without OOM. Upgrade to **T4 small GPU** ($0.40/hr) for real-time speed.

See [skyrecon_deploy_guide.md](../skyrecon_deploy_guide.md) for the full step-by-step deployment guide.

---

## 📱 Mobile App (PWA)

SkyRecon is **PWA-ready** (Progressive Web App). Users on Android and iOS can install it directly from the browser — no App Store needed.

### Android
1. Open the deployed URL in **Chrome**
2. Tap **⋮ Menu → Add to Home Screen**
3. Tap **Install** — it behaves exactly like a native app

### iOS (iPhone/iPad)
1. Open the deployed URL in **Safari** (Chrome on iOS does NOT support PWA install)
2. Tap **Share → Add to Home Screen**
3. Tap **Add** — app icon appears on home screen

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | Full Neon/PostgreSQL connection string (overrides individual DB_* vars) |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `skyrecon` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| `YOLO_MODEL` | `yolov8s.pt` | Base fallback model (`yolov8n.pt` on free tier) |
| `CONFIDENCE_THRESHOLD` | `0.5` | Detection confidence threshold (base YOLO) |
| `MIN_DISPLAY_CONFIDENCE` | `0.75` | Secondary confidence gate for heuristic detections (removed from YOLO loop; only used in heuristic path) |
| `ALLOWED_ORIGINS` | `http://localhost:3000, http://localhost:5173` | Comma-separated CORS origins |
| `UPLOAD_DIR` | `./uploads` | Directory for uploaded files |
| `SCREENSHOTS_DIR` | `./screenshots` | Directory for per-object screenshots |
| `REPORTS_DIR` | `./reports` | Directory for generated reports |

Copy `.env.example` to `.env` and fill in your values for local development.

---

## API Reference

Base URL (local): `http://localhost:8000`  
Base URL (deployed): `https://shibamkhadanga-skyrecon.hf.space`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | API status + GPU info |
| `GET` | `/api/v1/stream/proxy` | CORS proxy for camera streams (MJPEG, HLS, MP4) |
| `POST` | `/api/v1/analysis/upload` | Upload video/image, start AI |
| `POST` | `/api/v1/analysis/{id}/cancel` | Cancel a running analysis |
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
| `GET` | `/api/v1/analysis/category-stats` | Detection counts per category |
| `GET` | `/api/v1/analysis/weekly-stats` | Analyses + detections by day of week |
| `GET` | `/api/v1/categories/` | List all 25 categories |
| `POST` | `/api/v1/categories/` | Create category |
| `PUT` | `/api/v1/categories/{id}` | Update category |
| `DELETE` | `/api/v1/categories/{id}` | Delete category |
| `GET` | `/api/v1/dashboard/stats` | Platform statistics |
| `GET` | `/api/v1/dashboard/recent` | Recent analyses |
| `GET` | `/api/v1/dashboard/map-markers` | GIS map markers |
| `GET` | `/api/v1/stream/{id}` | SSE real-time progress stream |
| `POST` | `/api/v1/analysis/find-object` | Face-level CLIP matching + visual search in video or live stream |

Static file mounts (served directly by FastAPI):

| Mount | Directory | Contents |
|---|---|---|
| `/uploads/*` | `backend/uploads/` | Uploaded video/image files |
| `/screenshots/*` | `backend/screenshots/` | Full-frame annotated screenshots |
| `/reports/*` | `backend/reports/` | Generated PDF/DOCX report files |

Interactive docs: `http://localhost:8000/api/docs` or `https://shibamkhadanga-skyrecon.hf.space/api/docs`

---

## Weather Safety Bar

A `WeatherBar` component is shown at the top of Live Feed, Object Finder, and other pages. It fetches real-time weather from the [Open-Meteo API](https://open-meteo.com/) using the browser's GPS location (falls back to NIT Rourkela coordinates).

- Displays: temperature, wind speed, precipitation, cloud cover, weather condition
- Shows a green **Safe to fly** or red **Do NOT fly** badge based on thresholds:
  - Wind > 10 m/s, precipitation > 0.5 mm/h, temp < 0°C or > 45°C, cloud cover > 90%
- Plays an audio beep warning (Web Audio API) when unsafe conditions are detected
- No API key required — uses the free Open-Meteo public API

---

## Live Feed

Access at `/live`. Supported stream sources:

| Source | Protocol | Notes |
|---|---|---|
| FPV Receiver (USB) | `getUserMedia` | EWRF 5.8G OTG receiver — plug in, select from device list |
| MJPEG | HTTP | IP Webcam app, DJI WiFi, any MJPEG endpoint |
| HLS (.m3u8) | HTTP | Convert via mediamtx or FFmpeg on companion PC |
| Direct MP4 | HTTP | Any browser-compatible URL on local network |
| RTSP | — | Not natively supported in browsers; convert to HLS first |

Features:
- Telemetry HUD overlay (altitude, speed, battery, signal, temperature)
- In-browser recording via MediaRecorder API (WebM/VP9), saved to Recordings page
- Frame rotation controls (±90°) and fullscreen mode
- FPV Setup Guide for EWRF 5.8G OTG + Sologood VTX

---

## Object Finder

Access at `/find`. Two search modes for finding people or objects in drone footage.

### Visual Match Mode (Recommended for Person Search)
- Upload a target photo (face, person, vehicle, any object)
- Backend pipeline:
  1. **OpenCV Haar cascade** detects face in target photo → crops face region
  2. **CLIP** encodes both face crop and full image as embeddings
  3. For each video frame: **YOLO** detects people → **OpenCV** detects face in each person crop → **CLIP** compares face-to-face (70%) + body-to-body (30%)
  4. **CLIP dedup** across matches — same person seen multiple times → keep only the best match
  5. Results capped at top 20, sorted by confidence
- **PDF export** — styled report with thumbnails, timestamps, and confidence scores

### Facial Attributes Mode
- Filter by: gender, age group, hair color, facial hair, glasses, skin tone, clothing color
- Optionally upload a reference face photo to improve accuracy
- Backend: YOLO person detection → CLIP text prompt matching

### Common Features
- Video source: uploaded file **or** live stream (MJPEG / HLS / FPV USB)
- Backend: `POST /api/v1/analysis/find-object`
- Output: timestamp, confidence score, full-frame thumbnail with bbox overlay per match
- Export: PDF report with thumbnails and match data

---

## Mapping & Survey — Accuracy Features

### Per-Frame Floor Count
During processing, the system tracks the **maximum number of target objects detected in any single frame**. This is a hard lower bound — if YOLO sees 7 people in one frame, the final count cannot be less than 7. After CLIP dedup, if the unique count falls below this floor, the count is bumped back up. This prevents CLIP from over-merging distinct objects that look similar from aerial view.

### CLIP Visual Deduplication
After YOLO + ByteTrack processing is complete, a **post-processing dedup step** runs:

1. All unique person/object crops are encoded with CLIP (`openai/clip-vit-base-patch32`)
2. Pairwise cosine similarity is computed between all crop embeddings
3. If two crops have similarity > 0.88 AND were **NOT first seen in the same frame** (same-frame protection), the duplicate is merged away
4. After dedup, excess detection records are **deleted from the PostgreSQL database** — only the top N detections by confidence are kept
5. The per-frame floor is applied — final count = max(CLIP unique count, max per-frame count)
6. The final unique count is written to `total_objects` in the analysis record

### Same-Frame Protection
Detections first seen within 1.5 seconds of each other are **never merged**, even if visually similar. This prevents different people standing side-by-side from being collapsed into one count.

### Full-Frame Screenshots
Each detection screenshot shows the **entire video frame** with all detected objects highlighted by green bounding boxes, rather than individual cropped thumbnails. This provides visual context for verification.

---

## Recordings

Access at `/recordings`. All recordings captured from the Live Feed page are stored here.

- In-browser playback with native video controls
- Download as WebM or MP4
- Per-recording metadata: source protocol, duration, file size, capture date
- Sort by: name, date (newest/oldest), size, or duration
- Clear all with one click (blob URLs revoked to free memory)

---

## Detection Categories (25)

| Category | Model | Method |
|---|---|---|
| People | `skyrecon_visdrone.pt` | YOLOv8 + ByteTrack + CLIP visual dedup |
| Vehicles | `skyrecon_visdrone.pt` | YOLOv8 + ByteTrack + char filter |
| Animals | `skyrecon_visdrone.pt` | YOLOv8 + ByteTrack |
| Road Potholes | `skyrecon_rdd2022.pt` | YOLOv8 + dark blob heuristic |
| Fire & Smoke | `skyrecon_fire_smoke.pt` | YOLOv8 + HSV mask |
| Flood Water | `skyrecon_flood.pt` | YOLOv8 + SegFormer + HSV |
| Trees | `skyrecon_trees_plants.pt` | SegFormer-B2 + ExG index |
| Plants | `skyrecon_trees_plants.pt` | SegFormer-B2 + HSV green |
| Water Bodies | `yolov8s.pt` | SegFormer-B2 + HSV blue |
| Buildings | `skyrecon_buildings.pt` | YOLOv8 segmentation + solidity |
| Houses | `skyrecon_buildings.pt` | YOLOv8 segmentation + solidity |
| Roads | `yolov8s.pt` | HSV asphalt + elongation |
| Electric Poles | `yolov8s.pt` | Vertical edge detection |
| Street Lights | `yolov8s.pt` | Vertical edge detection |
| Solar Panels | `skyrecon_solar_panels.pt` | YOLOv8 segmentation + HSV mask |
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
- Full-frame annotated screenshots with bounding boxes, timestamps, and confidence
- AI planning recommendations

---

## Training Notebooks

Six Jupyter notebooks document the model fine-tuning process (located in `backend/`):

| Notebook | Dataset | Model |
|---|---|---|
| `SkyRecon_VisDrone_Training.ipynb` | VisDrone2019 | People & vehicles from aerial |
| `SkyRecon_FireSmoke_Training.ipynb` | Fire/Smoke dataset | Fire & smoke detection |
| `SkyRecon_Flood_Training.ipynb` | Flood imagery | Flood water detection |
| `SkyRecon_RDD2022_RoadDamage.ipynb` | RDD2022 | Road damage & potholes |
| `SkyRecon_Buildings_Training.ipynb` | Aerial buildings | Building segmentation |
| `SkyRecon_TreesPlants_Training.ipynb` | Aerial vegetation | Trees & plants detection |

---

<p align="center">
  <b>SkyRecon</b> – <em>AI Powered Aerial Intelligence & Disaster Monitoring Platform</em><br/>
  Built with ❤️ at NIT Rourkela · 2026 Drone Internship<br/>
  <strong>By: S. Khadanga</strong>
</p>
