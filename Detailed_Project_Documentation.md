# SkyRecon Platform - Detailed Project Documentation

## 1. Project Overview
SkyRecon is an advanced AI-powered drone intelligence and disaster monitoring platform. It integrates a responsive frontend built with React 19, Vite 8, and Tailwind CSS 4, and a robust backend powered by FastAPI and PostgreSQL. It features real-time video analysis using YOLOv8 + ByteTrack object tracking, SegFormer-B2 aerial segmentation, OpenCV heuristic detectors, and comprehensive PDF/DOCX report generation with embedded screenshots.

## 2. Comprehensive Directory Structure
```text
SkyRecon/
├── README.md                 # High-level project documentation
├── package.json              # Frontend dependencies and scripts
├── vite.config.js            # Vite bundler configuration (proxy /api → :8000)
├── tsconfig.json             # TypeScript configuration
├── index.html                # Entry HTML file (loads Google Fonts + favicon)
├── public/
│   └── skyrecon-favicon.svg  # Application favicon
├── src/                      # Frontend source code
│   ├── main.jsx              # React application entry point (BrowserRouter)
│   ├── App.jsx               # Main routing (7 routes, lazy loaded)
│   ├── index.css             # Global styles and Tailwind imports
│   ├── layouts/
│   │   └── AppLayout.jsx     # Sidebar + top navbar + breadcrumb (mobile responsive)
│   ├── components/
│   │   ├── Sidebar.jsx       # Collapsible navigation sidebar (3 sections + admin)
│   │   └── ui/               # Reusable UI components
│   │       ├── AnimatedCounter.jsx  # framer-motion animated number counter
│   │       ├── ConfidenceBar.jsx    # AI confidence level progress bar
│   │       ├── FileDropzone.jsx     # Drag-and-drop file upload with preview
│   │       ├── GlassCard.jsx        # Glassmorphism styled card wrapper
│   │       ├── NeonButton.jsx       # Themed button (primary/secondary/danger/ghost)
│   │       ├── RadarPulse.jsx       # Animated radar pulse SVG (landing page)
│   │       ├── SeverityBadge.jsx    # Color-coded severity level badge (1-5)
│   │       └── StatCard.jsx         # Statistics card with icon + animated counter
│   └── pages/
│       ├── LandingPage.jsx   # Module selection with animated stats + radar
│       ├── DashboardPage.jsx # Dashboard: stats, charts, recent analyses
│       ├── MappingPage.jsx   # Full mapping workspace: upload → configure → results
│       ├── DisasterPage.jsx  # Full disaster workspace: upload → configure → results
│       ├── MapPage.jsx       # GIS map: 3 tile layers, markers, heatmap, geolocation
│       ├── ReportsPage.jsx   # Report listing, filtering, and download
│       └── AdminPage.jsx     # Category CRUD + system status
└── backend/                  # Backend source code
    ├── requirements.txt      # Python dependencies
    ├── .env.example          # Environment variable template
    ├── sql/
    │   └── procedures.sql    # 12 PL/pgSQL stored procedures
    └── app/
        ├── __init__.py
        ├── main.py           # FastAPI app: CORS, routers, static mounts, startup
        ├── database.py       # SQLAlchemy engine, session, init_db, stored proc loader
        ├── ai/
        │   ├── video_processor.py    # Core mapping pipeline (YOLO + SegFormer + OpenCV)
        │   ├── disaster_engine.py    # Disaster detection + severity classification
        │   ├── area_calculator.py    # GSD-based area estimation from bboxes
        │   └── report_generator.py   # PDF (reportlab) + DOCX (python-docx) generator
        ├── api/v1/
        │   ├── analysis.py   # Upload, status polling, results, report endpoints
        │   ├── categories.py # Category CRUD endpoints
        │   └── dashboard.py  # Stats, recent analyses, map markers
        ├── core/
        │   ├── config.py     # Pydantic-settings based configuration
        │   └── seeder.py     # DB seeding: 25 categories with characteristics
        ├── models/
        │   └── models.py     # ORM: Category, Characteristic, Analysis, Detection, DisasterEvent, Report
        └── schemas/
            └── schemas.py    # Pydantic request/response schemas
```

## 3. Frontend Files: Functions, Modules, and APIs
**Location:** `src/` directory.
**Core Technologies:** React 19, React Router DOM 7, Tailwind CSS 4, Framer Motion 12, Recharts 3, React-Leaflet 5, Lucide React.

### 3.1. Page Components (`src/pages/`)
*   **LandingPage.jsx:** Entry point for users. Displays platform capabilities with animated stat counters (`AnimatedCounter`), a pulsing radar animation (`RadarPulse`), and module selection cards. Uses `framer-motion` for entrance animations and `lucide-react` for icons.
*   **DashboardPage.jsx:** High-level overview with four `StatCard` components showing total analyses, detections, reports, and alerts. Includes Recharts line/bar charts for detection trends and a recent analyses table. Fetches live data from `/api/v1/dashboard/stats` and `/api/v1/dashboard/recent`.
*   **MappingPage.jsx:** Full mapping workspace combining upload, configuration, and results in a single page. Uses `FileDropzone` for drag-and-drop video/image upload, category selection with characteristics filters, and displays real-time progress via status polling. Results panel shows detection counts, area coverage (m²), category breakdown charts, and embedded detection screenshots.
*   **DisasterPage.jsx:** Full disaster assessment workspace. Similar upload flow to MappingPage but triggers disaster analysis. Displays severity-ranked disaster events with `SeverityBadge`, resource estimation tables, and voice alerts via `window.speechSynthesis` for Level 5 critical threats.
*   **MapPage.jsx:** Full-screen GIS map view. See Section 6 for Map details.
*   **ReportsPage.jsx:** Lists all generated reports with filtering by type and format. Supports on-demand PDF/DOCX generation for completed analyses and direct download. Uses `GlassCard` for report cards and `NeonButton` for actions.
*   **AdminPage.jsx:** Category management interface with CRUD operations. Add/edit/delete detection categories and characteristics. Displays system status cards with `AnimatedCounter`.

### 3.2. UI Components (`src/components/ui/`)
*   **GlassCard.jsx:** Glassmorphism card wrapper with configurable hover effects, delay-based entrance animation, and border styling. Used extensively across all pages.
*   **AnimatedCounter.jsx:** Uses `framer-motion` to smoothly animate numerical values from 0 to target with configurable prefix/suffix.
*   **ConfidenceBar.jsx:** Horizontal progress bar showing AI confidence percentage with gradient coloring (green → yellow → red).
*   **FileDropzone.jsx:** Drag-and-drop file upload zone supporting video (MP4, MOV, AVI, MKV, WebM) and image (JPG, PNG, WebP) formats. Shows file preview, size, and format validation.
*   **NeonButton.jsx:** Multi-variant button component (primary/secondary/danger/ghost) with glow effects, icon support, and size options.
*   **RadarPulse.jsx:** SVG-based animated radar pulse used on the landing page hero section.
*   **SeverityBadge.jsx:** Color-coded badge displaying severity levels 1-5 with labels (Minor → Critical).
*   **StatCard.jsx:** Statistics display card combining a Lucide icon, label, and `AnimatedCounter` with configurable accent color.

## 4. Backend Files: Functions, Modules, and APIs
**Location:** `backend/` directory.
**Core Technologies:** Python 3.10+, FastAPI, SQLAlchemy 2.0, PostgreSQL, Pydantic v2, Ultralytics YOLOv8, OpenCV, PyTorch, HuggingFace Transformers.

### 4.1. Core Application (`backend/app/`)
*   **main.py:** FastAPI application entry point. Configures CORS middleware (allows `localhost:3000` and `localhost:5173`), registers API routers (`categories`, `analysis`, `dashboard`), mounts static file directories (`/uploads`, `/screenshots`, `/reports`), and runs `init_db()` on startup.
*   **database.py:** Establishes PostgreSQL connection via SQLAlchemy with connection pooling (pool_size=10, max_overflow=20). Auto-creates the target database if it doesn't exist. Runs `Base.metadata.create_all()`, installs stored procedures from `sql/procedures.sql`, and seeds default categories.
*   **models/models.py:** Defines 6 SQLAlchemy ORM models:
    *   `Category` — 25 detection categories with color/icon/active flag
    *   `Characteristic` — per-category filter options (e.g., vehicle type, tree health)
    *   `Analysis` — analysis job with status tracking and progress percentage
    *   `Detection` — individual object detection with bbox, confidence, screenshot
    *   `DisasterEvent` — disaster event with severity, affected area, resource estimation
    *   `Report` — generated report metadata with file path and status
*   **schemas/schemas.py:** Pydantic v2 request/response schemas for all API endpoints.
*   **core/config.py:** `pydantic-settings` based configuration loading from `.env` file. Defines database URL, storage paths, YOLO model, and confidence threshold.
*   **core/seeder.py:** Seeds 25 default detection categories with their characteristics on first startup.

### 4.2. AI Engine (`backend/app/ai/`)
*   **video_processor.py:** Core mapping analysis pipeline (~1200 lines). Implements:
    *   Multi-model YOLO inference with specialist model registry (5 fine-tuned models)
    *   SegFormer-B2 semantic segmentation for aerial categories (trees, water, buildings)
    *   12 OpenCV heuristic detectors (fire HSV, flood water, potholes, poles, solar panels, etc.)
    *   ByteTrack object tracking for unique count deduplication
    *   CLAHE frame enhancement for drone footage
    *   Aerial misclassification correction (kite→person remapping)
    *   Characteristics-based filtering (vehicle type, color, tree health)
    *   Grid-based spatial deduplication for heuristic detections
    *   Per-object screenshot capture with annotations
*   **disaster_engine.py:** Disaster analysis pipeline. Classifies 7 disaster types (fire, flood, structural, people, vehicles, trees, poles), computes severity 1-5 with confidence/area/density weighting, requires minimum frame occurrences to confirm events (reduces false positives), and generates resource estimation.
*   **area_calculator.py:** Converts normalized bounding boxes to real-world square meters using GSD (Ground Sampling Distance) lookup tables indexed by drone altitude.
*   **report_generator.py:** Generates PDF (via ReportLab) and DOCX (via python-docx) reports with embedded detection screenshots, category breakdown tables, coverage statistics, and AI recommendations.

### 4.3. Database Logic (`backend/sql/procedures.sql`)
*   Contains 12 PL/pgSQL stored procedures that offload complex operations to PostgreSQL:
    *   `create_analysis_job()` — creates analysis record and returns ID
    *   `record_detection()` — inserts detection with category mapping
    *   `record_disaster_event()` — inserts disaster event with severity
    *   `complete_analysis()` — marks analysis done with total count and time
    *   `delete_analysis_cascade()` — safely removes analysis and all related data
    *   `generate_report_record()` — creates report tracking record
    *   `mark_report_ready()` — updates report status with file path
    *   `seed_default_categories()` — idempotent category seeding
    *   And 4 more for stats aggregation and data management

## 5. API Endpoints Overview (FastAPI)

### Analysis (`/api/v1/analysis`)
*   `POST /upload` — Upload video/image, triggers background AI processing
*   `GET /{id}/status` — Poll processing progress (0-100%)
*   `GET /{id}/summary` — Full results with coverage stats and category breakdown
*   `GET /{id}/detections` — Detection list with optional category filter
*   `GET /{id}/disasters` — Disaster events for analysis
*   `POST /{id}/report` — Trigger async PDF/DOCX report generation
*   `GET /report/{id}/status` — Poll report generation status
*   `GET /report/{id}/download` — Stream report file for download
*   `GET /reports/` — List all reports with analysis metadata
*   `GET /` — List all analyses
*   `GET /{id}` — Get single analysis
*   `DELETE /{id}` — Delete analysis with cascade

### Categories (`/api/v1/categories`)
*   `GET /` — List all categories with characteristics
*   `POST /` — Create new category
*   `PUT /{id}` — Update category
*   `DELETE /{id}` — Delete category

### Dashboard (`/api/v1/dashboard`)
*   `GET /stats` — Platform-wide statistics
*   `GET /recent` — Recent analyses list
*   `GET /map-markers` — GIS markers for the map page

### Health
*   `GET /api/health` — API status, GPU availability, model info

## 6. Map Technology & Implementation
The mapping module (`src/pages/MapPage.jsx`) utilizes advanced GIS logic:
*   **Core Libraries:** `leaflet` and `react-leaflet`.
*   **Map Features:**
    *   **Tile Layers:** Supports dynamic switching between three map views:
        1. **Dark Mode:** Rendered via CartoCDN (`https://{s}.basemaps.cartocdn.com/dark_all...`)
        2. **Satellite View:** High-fidelity imagery via ArcGIS
        3. **Street View:** OpenStreetMap tiles
    *   **Geolocation (`navigator.geolocation`):** Auto-detects user location on mount and provides a "Locate Me" fly-to functionality using Leaflet's `map.flyTo` method.
    *   **Data Visualization:** Implements heatmap overlays representing detection density using `react-leaflet`'s `Circle` component with dynamic radii.
    *   **Custom Markers:** Uses `L.DivIcon` to render pulsating, color-coded HTML markers denoting severity levels. Markers display detection counts and severity badges.
    *   **Sidebar Panels:** Filterable marker list, layer controls, detection statistics, and detailed marker information panel.

## 7. AI Features & Video Analysis Engine
The AI capabilities are powered by `backend/app/ai/`:
*   **AI Inference Models:**
    *   5 specialized fine-tuned YOLO models for aerial detection (VisDrone, road damage, fire/smoke, flood, trees/plants)
    *   SegFormer-B2 (HuggingFace) for pixel-level semantic segmentation of trees, water, buildings
    *   12 OpenCV heuristic detectors for categories not covered by YOLO COCO classes
    *   Automatic model selection per category via specialist model registry
*   **Video Processing Workflow:**
    1.  **Ingestion:** Users upload drone footage via `FileDropzone.jsx` (supports MP4, MOV, AVI, MKV, WebM, JPG, PNG, WebP)
    2.  **Frame Extraction:** OpenCV extracts frames at configurable FPS (1-3 fps depending on category)
    3.  **Enhancement:** CLAHE contrast enhancement (skipped if frame contrast is sufficient)
    4.  **Inference:** YOLOv8 detection + ByteTrack tracking for YOLO categories; SegFormer + OpenCV for aerial categories
    5.  **Post-processing:** Aerial misclassification correction, characteristics filtering, grid-based deduplication
    6.  **Output:** Unique object counts, per-object screenshots, area coverage in m², and database records
*   **Dynamic Resource Estimator:** Algorithmic function that computes required Rescue Teams, Ambulances, Rescue Boats, and Support Staff based on severity multipliers.
*   **Audio Announcements:** Native browser `window.speechSynthesis` for vocal alarms on Level 5 critical threats.
*   **Reporting:** Generates professional PDF and DOCX reports with embedded screenshots, tables, and AI recommendations via ReportLab and python-docx.
