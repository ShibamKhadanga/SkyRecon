from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from ...database import get_db
from ...schemas import DashboardStats
from ...models.models import Detection, Category, DisasterEvent

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Returns actual platform statistics using get_dashboard_stats() PL/pgSQL function."""
    try:
        result = db.execute(text("SELECT * FROM get_dashboard_stats()")).first()
        if result:
            return DashboardStats(
                total_analyses=result.total_analyses or 0,
                total_detections=result.total_detections or 0,
                total_reports=result.total_reports or 0,
                active_alerts=result.active_alerts or 0,
            )
    except Exception as e:
        print(f"⚠️ Error calling get_dashboard_stats stored procedure: {e}")
    
    # Fallback to zeros if procedure fails
    return DashboardStats(
        total_analyses=0,
        total_detections=0,
        total_reports=0,
        active_alerts=0,
    )


@router.get("/recent-analyses")
def get_recent_analyses(db: Session = Depends(get_db)):
    """Returns the most recent analyses using get_recent_analyses() PL/pgSQL function."""
    try:
        result = db.execute(text("SELECT * FROM get_recent_analyses(5)")).all()
        return [
            {
                "id": r.id,
                "project_name": r.project_name,
                "status": r.status,
                "total_objects": r.total_objects,
                "detection_mode": r.detection_mode,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in result
        ]
    except Exception as e:
        print(f"⚠️ Error calling get_recent_analyses stored procedure: {e}")
        return []


@router.get("/map-markers")
def get_map_markers(db: Session = Depends(get_db)):
    """Returns active map markers dynamically queried from actual DB detections & disaster events."""
    markers = []
    
    # ── 1. Fetch Detections with coordinates ──
    try:
        detections = db.query(
            Detection.id,
            Detection.gps_lat,
            Detection.gps_lon,
            Detection.label,
            Detection.confidence,
            Category.name.label("cat_name"),
            Category.color.label("cat_color")
        ).join(Category, Detection.category_id == Category.id).filter(
            Detection.gps_lat.isnot(None),
            Detection.gps_lon.isnot(None)
        ).all()

        for d in detections:
            # Estimate severity from confidence
            severity = 3 if d.confidence > 0.9 else (2 if d.confidence > 0.8 else 1)
            markers.append({
                "id": f"det-{d.id}",
                "lat": d.gps_lat,
                "lon": d.gps_lon,
                "label": f"{d.cat_name}: {d.label}",
                "type": d.cat_name.lower(),
                "color": d.cat_color,
                "severity": severity,
                "detections": 1
            })
    except Exception as e:
        print(f"⚠️ Error querying map-marker detections: {e}")

    # ── 2. Fetch Disaster Events with coordinates ──
    try:
        disasters = db.query(
            DisasterEvent.id,
            DisasterEvent.gps_lat,
            DisasterEvent.gps_lon,
            DisasterEvent.disaster_type,
            DisasterEvent.severity,
            DisasterEvent.confidence
        ).filter(
            DisasterEvent.gps_lat.isnot(None),
            DisasterEvent.gps_lon.isnot(None)
        ).all()

        for d in disasters:
            markers.append({
                "id": f"dis-{d.id}",
                "lat": d.gps_lat,
                "lon": d.gps_lon,
                "label": f"🚨 Disaster: {d.disaster_type.upper()}",
                "type": "disaster",
                "color": "#ef4444",  # High-contrast disaster red
                "severity": d.severity,
                "detections": 5
            })
    except Exception as e:
        print(f"⚠️ Error querying map-marker disasters: {e}")

    # Fallback to static items if DB has absolutely no coordinate data
    if not markers:
        return [
            {"id": "mock-1", "lat": 28.6139, "lon": 77.2090, "label": "Traffic Zone A (Mock)", "type": "vehicles", "severity": 2, "detections": 42},
            {"id": "mock-2", "lat": 28.6200, "lon": 77.2150, "label": "Industrial Fire (Mock)", "type": "fire & smoke", "severity": 4, "detections": 15},
            {"id": "mock-3", "lat": 28.6050, "lon": 77.2000, "label": "Srinagar Flood Zone (Mock)", "type": "disaster", "severity": 5, "detections": 8},
        ]

    return markers
