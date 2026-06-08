from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .core.config import settings
from .database import init_db
from .api.v1 import categories, analysis, dashboard, stream
import os

# Create directories BEFORE mounting — fixes startup crash on fresh containers
for d in [settings.UPLOAD_DIR, settings.SCREENSHOTS_DIR, settings.REPORTS_DIR]:
    os.makedirs(d, exist_ok=True)

# Initialize FastAPI
app = FastAPI(
    title="SkyRecon API",
    description="AI Powered Drone Intelligence Platform – Backend API",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(categories.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(stream.router,    prefix="/api/v1")

# Serve static files (directories now guaranteed to exist)
app.mount("/uploads",     StaticFiles(directory=settings.UPLOAD_DIR),      name="uploads")
app.mount("/screenshots", StaticFiles(directory=settings.SCREENSHOTS_DIR), name="screenshots")
app.mount("/reports",     StaticFiles(directory=settings.REPORTS_DIR),     name="reports")


@app.on_event("startup")
def startup():
    init_db()
    print("[API] SkyRecon API started")
    print(f"[API] Docs: http://localhost:7860/api/docs")
    try:
        from .ai.video_processor import _get_model
        _get_model(settings.YOLO_MODEL)
        print(f"[API] Base model '{settings.YOLO_MODEL}' pre-loaded.")
    except Exception as e:
        print(f"[API] Model pre-load skipped: {e}")
    try:
        from .ai.video_processor import _get_model
        _get_model(settings.YOLO_MODEL)
        print(f"[API] Base model '{settings.YOLO_MODEL}' pre-loaded.")
    except Exception as e:
        print(f"[API] Model pre-load skipped: {e}")


@app.get("/api/health")
def health_check():
    import torch
    gpu_available = torch.cuda.is_available()
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "ai_engine": "ready",
        "gpu": gpu_available,
        "device": "cuda" if gpu_available else "cpu",
        "models": {
            "yolov8": settings.YOLO_MODEL,
            "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        }
    }