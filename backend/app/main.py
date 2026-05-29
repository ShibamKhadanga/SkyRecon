from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .core.config import settings
from .database import init_db
from .api.v1 import categories, analysis, dashboard

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

# Serve uploaded videos, screenshots, and generated reports as static files
app.mount("/uploads",     StaticFiles(directory=settings.UPLOAD_DIR),      name="uploads")
app.mount("/screenshots", StaticFiles(directory=settings.SCREENSHOTS_DIR), name="screenshots")
app.mount("/reports",     StaticFiles(directory=settings.REPORTS_DIR),     name="reports")


@app.on_event("startup")
def startup():
    # Ensure all storage directories exist before mounting
    import os
    for d in [settings.UPLOAD_DIR, settings.SCREENSHOTS_DIR, settings.REPORTS_DIR]:
        os.makedirs(d, exist_ok=True)
    init_db()
    print("[API] SkyRecon API started")
    print(f"[API] Docs: http://localhost:8000/api/docs")


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
