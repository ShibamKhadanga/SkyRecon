"""
SkyRecon – Analysis API
Handles video upload, triggers real AI processing as background tasks,
and exposes results + report generation endpoints.
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import shutil, uuid, os, logging

from ...database import get_db, SessionLocal
from ...models.models import Analysis, Detection, DisasterEvent
from ...schemas import AnalysisResponse, DetectionResponse, DisasterEventResponse
from ...core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ── Background task runners (use their own DB session) ────────────────────────

def _run_mapping_task(
    analysis_id: int,
    video_path: str,
    selected_category: str,
    characteristics: dict,
    detection_mode: str,
    custom_query: str,
):
    """Runs in background thread — owns its own DB session."""
    db = SessionLocal()
    try:
        from ...ai.video_processor import run_mapping_analysis
        run_mapping_analysis(
            analysis_id=analysis_id,
            video_path=video_path,
            selected_category=selected_category,
            characteristics=characteristics,
            detection_mode=detection_mode,
            custom_query=custom_query,
            db=db,
        )
    except Exception as e:
        logger.error(f"[BG] Mapping task failed for analysis {analysis_id}: {e}", exc_info=True)
        try:
            db.execute(text("UPDATE analyses SET status='failed' WHERE id=:id"), {"id": analysis_id})
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _run_disaster_task(analysis_id: int, video_path: str):
    """Runs in background thread — owns its own DB session."""
    db = SessionLocal()
    try:
        from ...ai.disaster_engine import run_disaster_analysis
        run_disaster_analysis(
            analysis_id=analysis_id,
            video_path=video_path,
            db=db,
        )
    except Exception as e:
        logger.error(f"[BG] Disaster task failed for analysis {analysis_id}: {e}", exc_info=True)
        try:
            db.execute(text("UPDATE analyses SET status='failed' WHERE id=:id"), {"id": analysis_id})
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _run_report_task(analysis_id: int, report_id: int, report_type: str, fmt: str):
    """Generates report in background and marks it ready."""
    db = SessionLocal()
    try:
        from ...ai.report_generator import generate_report
        file_path = generate_report(analysis_id, report_type, fmt, db)
        db.execute(
            text("SELECT mark_report_ready(:report_id, :file_path)"),
            {"report_id": report_id, "file_path": file_path}
        )
        db.commit()
        logger.info(f"[BG] Report {report_id} ready at {file_path}")
    except Exception as e:
        logger.error(f"[BG] Report generation failed for analysis {analysis_id}: {e}")
        db.execute(
            text("UPDATE reports SET status='failed' WHERE id=:id"),
            {"id": report_id}
        )
        db.commit()
    finally:
        db.close()


# ── Cancel analysis ─────────────────────────────────────────────────────

_cancelled_jobs: set[int] = set()  # checked by AI pipeline each frame

@router.post("/{analysis_id}/cancel")
def cancel_analysis(analysis_id: int, db: Session = Depends(get_db)):
    row = db.execute(text("SELECT status FROM analyses WHERE id=:id"), {"id": analysis_id}).first()
    if not row:
        raise HTTPException(404, "Analysis not found")
    if row.status not in ("processing", "pending"):
        raise HTTPException(400, f"Cannot cancel — status is '{row.status}'")
    _cancelled_jobs.add(analysis_id)
    db.execute(text("UPDATE analyses SET status='cancelled' WHERE id=:id"), {"id": analysis_id})
    db.commit()
    return {"message": f"Analysis {analysis_id} cancelled."}


def is_cancelled(analysis_id: int) -> bool:
    return analysis_id in _cancelled_jobs


# ── Find Object endpoint ──────────────────────────────────────────────────────

@router.post("/find-object")
async def find_object(
    target_image: UploadFile = File(...),
    video: Optional[UploadFile] = File(None),
    live_url: Optional[str] = Form(None),
):
    """
    Given a target image and a video (uploaded or live URL),
    finds all frames where the target object/person appears.
    Uses CLIP for feature similarity matching.
    """
    import cv2, numpy as np, tempfile, base64
    from PIL import Image as PILImage
    import io

    # ── Load CLIP ──
    try:
        import torch
        from transformers import CLIPProcessor, CLIPModel
        device = "cuda" if torch.cuda.is_available() else "cpu"
        clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
        clip_proc  = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    except Exception as e:
        raise HTTPException(500, f"Failed to load CLIP model: {e}")

    # ── Encode target image ──
    target_bytes = await target_image.read()
    target_pil   = PILImage.open(io.BytesIO(target_bytes)).convert("RGB")
    with torch.no_grad():
        t_inputs = clip_proc(images=target_pil, return_tensors="pt")
        # Pass only pixel_values to get_image_features to avoid unexpected key errors
        target_feat = clip_model.get_image_features(pixel_values=t_inputs["pixel_values"].to(device))
        target_feat = target_feat / target_feat.norm(dim=-1, keepdim=True)

    # ── Get video path ──
    tmp_video = None
    if video:
        suffix = os.path.splitext(video.filename)[1] or ".mp4"
        tmp_video = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        shutil.copyfileobj(video.file, tmp_video)
        tmp_video.flush()
        video_path = tmp_video.name
    elif live_url:
        video_path = live_url
    else:
        raise HTTPException(400, "Provide either a video file or live_url")

    # ── Scan frames ──
    SIMILARITY_THRESHOLD = 0.72
    FRAME_INTERVAL = 30   # check every 30 frames (~1s at 30fps)
    matches = []

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise HTTPException(400, "Cannot open video source")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % FRAME_INTERVAL == 0:
                timestamp = frame_idx / fps

                # Convert frame to PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_pil = PILImage.fromarray(frame_rgb)

                # CLIP similarity
                with torch.no_grad():
                    f_inputs = clip_proc(images=frame_pil, return_tensors="pt")
                    frame_feat = clip_model.get_image_features(pixel_values=f_inputs["pixel_values"].to(device))
                    frame_feat = frame_feat / frame_feat.norm(dim=-1, keepdim=True)
                    similarity = float((target_feat @ frame_feat.T).squeeze())

                if similarity >= SIMILARITY_THRESHOLD:
                    # Capture thumbnail as base64 JPEG
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    thumb_b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode()

                    matches.append({
                        "timestamp":   round(timestamp, 2),
                        "confidence":  round(similarity, 3),
                        "description": f"Match at {int(timestamp//60):02d}:{int(timestamp%60):02d} — similarity {similarity:.0%}",
                        "thumbnail":   thumb_b64,
                    })

            frame_idx += 1

        cap.release()
    finally:
        if tmp_video:
            try: os.unlink(tmp_video.name)
            except: pass

    # Sort by confidence descending
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return {"matches": matches, "total_scanned": frame_idx, "threshold": SIMILARITY_THRESHOLD}


# ── Upload & start ─────────────────────────────────────────────────────────────

@router.post("/upload", response_model=AnalysisResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: str = Form("Untitled Analysis"),
    description: str = Form(""),
    location: str = Form(""),
    drone_model: str = Form(""),
    analysis_type: str = Form("mapping"),       # "mapping" or "disaster"
    detection_mode: str = Form("standard"),     # "standard" or "custom"
    selected_category: str = Form("Vehicles"),  # category name for mapping
    characteristics: str = Form("{}"),          # JSON string of filters
    custom_query: str = Form(""),
    db: Session = Depends(get_db),
):
    allowed_types = [
        "video/mp4", "video/quicktime", "video/x-msvideo",
        "video/x-matroska", "video/webm",
        "image/jpeg", "image/png", "image/webp", "image/bmp",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}. Supported: MP4, MOV, AVI, MKV, WebM, JPG, PNG, WebP")

    is_image = file.content_type.startswith("image/")

    # Save uploaded file
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}{ext}")

    with open(file_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    # Create analysis record — store selected_category and characteristics in custom_query field
    # Format: "CATEGORY:Vehicles|CHARS:{...}|QUERY:..."
    import json
    try:
        chars = json.loads(characteristics)
    except Exception:
        chars = {}

    # Build a rich custom_query string that stores all analysis context
    analysis_context = json.dumps({
        "selected_category": selected_category,
        "characteristics": chars,
        "custom_query": custom_query,
        "analysis_type": analysis_type,
    })

    try:
        res = db.execute(
            text("""
                SELECT create_analysis_job(
                    :project_name, :description, :location,
                    :drone_model, :detection_mode, :custom_query
                )
            """),
            {
                "project_name": project_name,
                "description": description,
                "location": location,
                "drone_model": drone_model,
                "detection_mode": detection_mode,
                "custom_query": analysis_context,
            }
        )
        analysis_id = res.scalar()
        db.execute(
            text("UPDATE analyses SET video_path=:vp WHERE id=:id"),
            {"vp": f"/uploads/{file_id}{ext}", "id": analysis_id}
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"DB error creating analysis: {e}")

    # Kick off the real AI pipeline in the background
    if analysis_type == "disaster":
        background_tasks.add_task(_run_disaster_task, analysis_id, file_path)
    else:
        background_tasks.add_task(
            _run_mapping_task,
            analysis_id, file_path,
            selected_category, chars,
            detection_mode, custom_query,
        )

    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    return analysis


@router.get("/{analysis_id}/status")
def get_status(analysis_id: int, db: Session = Depends(get_db)):
    """Poll this endpoint to track real processing progress."""
    row = db.execute(
        text("SELECT status, total_objects, processing_time, description FROM analyses WHERE id=:id"),
        {"id": analysis_id}
    ).first()
    if not row:
        raise HTTPException(404, "Analysis not found")

    # Progress is written into description as '||PROGRESS||NN'
    progress = 0
    if row.description and "||PROGRESS||" in row.description:
        try:
            progress = int(row.description.split("||PROGRESS||")[-1])
        except Exception:
            progress = 0
    if row.status == "completed":
        progress = 100
    elif row.status == "processing":
        progress = max(5, progress)

    return {
        "analysis_id": analysis_id,
        "status": row.status,
        "total_objects": row.total_objects,
        "processing_time": row.processing_time,
        "progress": progress,
    }


@router.get("/{analysis_id}/detections", response_model=List[DetectionResponse])
def get_detections(
    analysis_id: int,
    category: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Returns real detections from the DB for a completed analysis."""
    query = """
        SELECT d.*, c.name as category_name
        FROM detections d
        LEFT JOIN categories c ON d.category_id = c.id
        WHERE d.analysis_id = :id
    """
    params: dict = {"id": analysis_id}
    if category:
        query += " AND c.name ILIKE :cat"
        params["cat"] = f"%{category}%"
    query += " ORDER BY d.confidence DESC LIMIT :limit"
    params["limit"] = limit

    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/{analysis_id}/disasters", response_model=List[DisasterEventResponse])
def get_disaster_events(analysis_id: int, db: Session = Depends(get_db)):
    """Returns real disaster events for a completed disaster analysis."""
    rows = db.execute(
        text("SELECT * FROM disaster_events WHERE analysis_id=:id ORDER BY severity DESC"),
        {"id": analysis_id}
    ).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/{analysis_id}/summary")
def get_summary(analysis_id: int, db: Session = Depends(get_db)):
    """Returns a full summary with coverage stats — used by the frontend results page."""
    from ...ai.area_calculator import compute_coverage_stats

    analysis = db.execute(
        text("SELECT * FROM analyses WHERE id=:id"), {"id": analysis_id}
    ).first()
    if not analysis:
        raise HTTPException(404, "Analysis not found")

    detections = db.execute(
        text("""
            SELECT d.bbox_w, d.bbox_h, d.confidence, d.timestamp, d.label,
                   c.name as category_name, c.color as category_color
            FROM detections d
            LEFT JOIN categories c ON d.category_id = c.id
            WHERE d.analysis_id = :id
        """),
        {"id": analysis_id}
    ).fetchall()
    det_list = [dict(r._mapping) for r in detections]

    disasters = db.execute(
        text("SELECT * FROM disaster_events WHERE analysis_id=:id ORDER BY severity DESC"),
        {"id": analysis_id}
    ).fetchall()

    coverage = compute_coverage_stats(det_list)

    # Category breakdown
    cat_counts: dict = {}
    for d in det_list:
        cat = d.get("category_name", "Unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    return {
        "analysis_id": analysis_id,
        "status": analysis.status,
        "project_name": analysis.project_name,
        "location": analysis.location,
        "drone_model": analysis.drone_model,
        "detection_mode": analysis.detection_mode,
        "total_detections": analysis.total_objects,  # authoritative unique count from tracker
        "processing_time": analysis.processing_time,
        "coverage": coverage,
        "category_breakdown": cat_counts,
        "disaster_events": [dict(r._mapping) for r in disasters],
        "top_detections": det_list[:10],
    }


# ── Report generation ──────────────────────────────────────────────────────────

@router.post("/{analysis_id}/report")
def request_report(
    analysis_id: int,
    background_tasks: BackgroundTasks,
    report_type: str = "mapping",
    fmt: str = "pdf",
    db: Session = Depends(get_db),
):
    """Triggers async report generation. Returns report_id to poll."""
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(404, "Analysis not found")
    if analysis.status != "completed":
        raise HTTPException(400, f"Analysis is not completed yet (status: {analysis.status})")

    res = db.execute(
        text("SELECT generate_report_record(:aid, :title, :rtype, :fmt)"),
        {
            "aid": analysis_id,
            "title": f"{analysis.project_name} – {report_type.title()} Report",
            "rtype": report_type,
            "fmt": fmt,
        }
    )
    report_id = res.scalar()
    db.commit()

    background_tasks.add_task(_run_report_task, analysis_id, report_id, report_type, fmt)

    return {"report_id": report_id, "status": "generating", "format": fmt}


@router.get("/report/{report_id}/status")
def report_status(report_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT id, status, file_path, format FROM reports WHERE id=:id"),
        {"id": report_id}
    ).first()
    if not row:
        raise HTTPException(404, "Report not found")
    return dict(row._mapping)


@router.get("/report/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    """Streams the generated report file for download."""
    row = db.execute(
        text("SELECT status, file_path, format FROM reports WHERE id=:id"),
        {"id": report_id}
    ).first()
    if not row:
        raise HTTPException(404, "Report not found")
    if row.status != "ready":
        raise HTTPException(400, f"Report not ready yet (status: {row.status})")

    # file_path stored as "/reports/filename.pdf" — resolve to absolute
    rel = row.file_path.lstrip("/")
    abs_path = os.path.join(os.path.dirname(settings.REPORTS_DIR), rel)
    if not os.path.exists(abs_path):
        # Try direct path
        abs_path = os.path.join(settings.REPORTS_DIR, os.path.basename(row.file_path))
    if not os.path.exists(abs_path):
        raise HTTPException(404, "Report file not found on disk")

    media_type = "application/pdf" if row.format == "pdf" else \
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(abs_path, media_type=media_type, filename=os.path.basename(abs_path))


# ── Standard CRUD ──────────────────────────────────────────────────────────────

@router.get("/reports/", tags=["Reports"])
def list_all_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Returns all reports joined with analysis metadata for the Reports page."""
    rows = db.execute(
        text("""
            SELECT r.id, r.analysis_id, r.title, r.report_type, r.format,
                   r.status, r.file_path, r.created_at,
                   a.project_name, a.total_objects, a.processing_time, a.detection_mode
            FROM reports r
            LEFT JOIN analyses a ON r.analysis_id = a.id
            ORDER BY r.created_at DESC
            LIMIT :limit OFFSET :skip
        """),
        {"limit": limit, "skip": skip}
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r._mapping)
        d["title"] = d["title"] or d.get("project_name") or f"Analysis #{d['analysis_id']}"
        result.append(d)

    # Also include completed analyses that have no report record yet
    existing_aids = {r["analysis_id"] for r in result}
    orphans = db.execute(
        text("""
            SELECT id, project_name, total_objects, processing_time,
                   detection_mode, completed_at, created_at
            FROM analyses
            WHERE status = 'completed'
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"limit": limit}
    ).fetchall()
    for a in orphans:
        if a.id not in existing_aids:
            result.append({
                "id": None,
                "analysis_id": a.id,
                "title": a.project_name or f"Analysis #{a.id}",
                "report_type": "disaster" if a.detection_mode == "disaster" else "mapping",
                "format": "pdf",
                "status": "ready",
                "file_path": None,
                "created_at": a.completed_at or a.created_at,
                "total_objects": a.total_objects or 0,
                "processing_time": a.processing_time,
                "detection_mode": a.detection_mode,
            })
    return result


@router.get("/category-stats")
def get_category_stats(db: Session = Depends(get_db)):
    """Returns aggregated detection counts per category across all completed analyses."""
    rows = db.execute(
        text("""
            SELECT c.name, c.color, COUNT(d.id) as count
            FROM detections d
            JOIN categories c ON d.category_id = c.id
            JOIN analyses a ON d.analysis_id = a.id
            WHERE a.status = 'completed'
            GROUP BY c.name, c.color
            ORDER BY count DESC
            LIMIT 8
        """)
    ).fetchall()
    return [{"name": r.name, "color": r.color, "value": r.count} for r in rows]


@router.get("/weekly-stats")
def get_weekly_stats(db: Session = Depends(get_db)):
    """Returns analyses and detections grouped by day of week for the chart."""
    rows = db.execute(
        text("""
            SELECT
                TO_CHAR(created_at, 'Dy') as day,
                EXTRACT(DOW FROM created_at) as dow,
                COUNT(*) as analyses,
                COALESCE(SUM(total_objects), 0) as detections
            FROM analyses
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY day, dow
            ORDER BY dow
        """)
    ).fetchall()
    return [{"name": r.day, "analyses": r.analyses, "detections": int(r.detections)} for r in rows]


def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    a = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not a:
        raise HTTPException(404, "Analysis not found")
    return a


@router.get("/", response_model=List[AnalysisResponse])
def list_analyses(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Analysis).order_by(Analysis.created_at.desc()).offset(skip).limit(limit).all()


@router.delete("/{analysis_id}")
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)):
    a = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not a:
        raise HTTPException(404, "Analysis not found")
    try:
        db.execute(text("SELECT delete_analysis_cascade(:id)"), {"id": analysis_id})
        db.commit()
        return {"message": f"Analysis {analysis_id} deleted."}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Delete failed: {e}")
