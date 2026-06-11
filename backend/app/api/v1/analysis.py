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

# CLIP model cache — load once per process
_clip_cache: dict = {}

def _get_clip_model():
    """
    Load CLIP model and processor, cached after first load.
    Tries clip-vit-base-patch32 first (faster, known to work), then
    upgrades to clip-vit-large-patch14 if available.
    """
    if "model" in _clip_cache:
        return _clip_cache["model"], _clip_cache["proc"], _clip_cache["device"]
    import torch
    from transformers import CLIPProcessor, CLIPModel
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Try base model first (smaller, known working on this system)
    for model_name in [
        "openai/clip-vit-base-patch32",
        "openai/clip-vit-large-patch14",
    ]:
        try:
            model = CLIPModel.from_pretrained(model_name).to(device)
            proc = CLIPProcessor.from_pretrained(model_name)
            model.eval()
            _clip_cache["model"] = model
            _clip_cache["proc"] = proc
            _clip_cache["device"] = device
            logger.info(f"[FindObject] Loaded CLIP model: {model_name} on {device}")
            return model, proc, device
        except Exception as e:
            logger.warning(f"[FindObject] Failed to load {model_name}: {e}")
            continue
    raise RuntimeError("Could not load any CLIP model")


def _to_tensor(feat):
    """Extract a plain tensor from CLIP output (handles structured outputs)."""
    import torch
    if isinstance(feat, torch.Tensor):
        return feat
    # Some transformers versions return BaseModelOutputWithPooling
    if hasattr(feat, 'pooler_output'):
        return feat.pooler_output
    if hasattr(feat, 'last_hidden_state'):
        return feat.last_hidden_state[:, 0]
    # Fallback: try indexing
    try:
        return feat[0]
    except Exception:
        return feat


@router.post("/find-object")
async def find_object(
    target_image: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    live_url: Optional[str] = Form(None),
    search_mode: str = Form("visual"),
    facial_attributes: str = Form("{}"),
):
    """
    Finds a target person/object in drone video footage.

    Pipeline:
    1. YOLO detects all people in each sampled frame
    2. CLIP encodes each person crop
    3. Cosine similarity is computed between target image and each crop
    4. Matches above threshold are returned with timestamps and thumbnails

    This replaces the old approach that compared against full frames (which
    never worked because CLIP similarity between a face crop and a full
    aerial scene with buildings/trees/sky is extremely low).
    """
    import traceback as _tb
    try:
        return await _find_object_impl(
            target_image=target_image, video=video, live_url=live_url,
            search_mode=search_mode, facial_attributes=facial_attributes,
        )
    except HTTPException:
        raise  # let FastAPI handle these normally
    except Exception as e:
        raise HTTPException(500, detail=f"{type(e).__name__}: {e}\n{_tb.format_exc()}")


async def _find_object_impl(
    target_image, video, live_url, search_mode, facial_attributes
):
    import cv2, numpy as np, tempfile, base64, json
    from PIL import Image as PILImage
    import io

    # ── Load models ──
    try:
        import torch
        clip_model, clip_proc, device = _get_clip_model()
    except Exception as e:
        raise HTTPException(500, f"Failed to load CLIP model: {e}")

    try:
        from ultralytics import YOLO
        yolo = YOLO("yolov8s.pt")
    except Exception as e:
        raise HTTPException(500, f"Failed to load YOLO model: {e}")

    # ── Face detection helper using OpenCV Haar cascade ──
    _face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    def _detect_face_crop(img_bgr):
        """Detect the largest face in a BGR image and return the face crop (BGR).
        Returns None if no face found."""
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        faces = _face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20)
        )
        if len(faces) == 0:
            return None
        # Pick the largest face
        areas = [w * h for (x, y, w, h) in faces]
        idx = np.argmax(areas)
        fx, fy, fw, fh = faces[idx]
        # Add 20% padding around face for hair/chin context
        pad = int(0.2 * max(fw, fh))
        ih, iw = img_bgr.shape[:2]
        fx1 = max(0, fx - pad)
        fy1 = max(0, fy - pad)
        fx2 = min(iw, fx + fw + pad)
        fy2 = min(ih, fy + fh + pad)
        return img_bgr[fy1:fy2, fx1:fx2]

    def _clip_embed_image(img_bgr):
        """Get CLIP embedding for a BGR image."""
        pil = PILImage.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
        with torch.no_grad():
            inp = clip_proc(images=pil, return_tensors="pt")
            feat = _to_tensor(clip_model.get_image_features(
                pixel_values=inp["pixel_values"].to(device)
            ))
            feat = feat / feat.norm(dim=-1, keepdim=True)
        return feat

    # ── Encode target image (face-level + full-image) ──
    target_feat = None       # full image embedding (fallback)
    target_face_feat = None  # face-only embedding (primary)
    if target_image:
        target_bytes = await target_image.read()
        target_np = np.frombuffer(target_bytes, dtype=np.uint8)
        target_bgr = cv2.imdecode(target_np, cv2.IMREAD_COLOR)

        # Full-image CLIP embedding (fallback)
        target_feat = _clip_embed_image(target_bgr)

        # Try to extract face for face-level matching
        face_crop = _detect_face_crop(target_bgr)
        if face_crop is not None and face_crop.size > 0:
            target_face_feat = _clip_embed_image(face_crop)
            logger.info("[FindObject] Face detected in target image — using face-level matching")

    # ── Build text prompts for facial attribute mode ──
    text_feats = None
    if search_mode == "facial":
        try:
            attrs = json.loads(facial_attributes) if isinstance(facial_attributes, str) else facial_attributes
        except Exception:
            attrs = {}
        prompts = []
        parts = []
        gender = attrs.get("gender", "")
        if gender:
            parts.append(f"a {gender} person")
        clothing = attrs.get("clothing_color", "")
        if clothing:
            parts.append(f"wearing {clothing} clothing")
        hair = attrs.get("hair_color", "")
        if hair:
            parts.append(f"with {hair} hair")
        age = attrs.get("age_group", "")
        if age:
            parts.append(f"who is {age}")
        glasses = attrs.get("glasses", "")
        if glasses == "yes":
            parts.append("wearing glasses")
        elif glasses == "no":
            parts.append("without glasses")
        skin = attrs.get("skin_tone", "")
        if skin:
            parts.append(f"with {skin} skin")

        if parts:
            prompts = [" ".join(parts)]
        if prompts:
            with torch.no_grad():
                t_in = clip_proc(text=prompts, return_tensors="pt", padding=True)
                # Move individual tensors to device (some transformers versions
                # don't support .to(device) on BatchEncoding)
                t_in_device = {k: v.to(device) if hasattr(v, 'to') else v for k, v in t_in.items()}
                text_feats = _to_tensor(clip_model.get_text_features(**t_in_device))
                text_feats = text_feats / text_feats.norm(dim=-1, keepdim=True)

    if target_feat is None and text_feats is None:
        raise HTTPException(400, "Provide a target image or facial attributes to search for")

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

    # ── Scan frames with YOLO person detection + CLIP crop matching ──
    SIMILARITY_THRESHOLD = 0.62   # CLIP person-crop similarity — raised from 0.52
    FRAME_INTERVAL = 15           # every 15 frames (~0.5s at 30fps)
    YOLO_PERSON_CONF = 0.25      # confidence for YOLO person detection
    MAX_MATCHES = 20             # cap results to top N
    DEDUP_SIM = 0.80             # same-person dedup threshold (CLIP crop-to-crop)
    matches = []
    match_feats = []              # CLIP embeddings of matched crops for dedup

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

                # Step 1: Detect all people in this frame using YOLO
                yolo_results = yolo(
                    frame, verbose=False, conf=YOLO_PERSON_CONF,
                    classes=[0],  # class 0 = person in COCO
                )

                for result in yolo_results:
                    if result.boxes is None:
                        continue
                    for box in result.boxes:
                        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                        h_frame, w_frame = frame.shape[:2]

                        # Clamp to frame bounds
                        x1 = max(0, x1); y1 = max(0, y1)
                        x2 = min(w_frame, x2); y2 = min(h_frame, y2)

                        # Skip tiny crops
                        crop_w = x2 - x1
                        crop_h = y2 - y1
                        if crop_w < 10 or crop_h < 10:
                            continue

                        # Step 2: Extract person crop and encode with CLIP
                        person_crop = frame[y1:y2, x1:x2]
                        if person_crop.size == 0:
                            continue

                        # Get full-body CLIP embedding
                        crop_feat = _clip_embed_image(person_crop)

                        # Try face-level matching if we have a target face
                        crop_face_feat = None
                        if target_face_feat is not None:
                            face_in_crop = _detect_face_crop(person_crop)
                            if face_in_crop is not None and face_in_crop.size > 0:
                                crop_face_feat = _clip_embed_image(face_in_crop)

                        # Step 3: Compute similarity scores
                        best_score = 0.0

                        # Score against target image (visual match)
                        if target_feat is not None:
                            # Primary: face-to-face comparison (much more accurate)
                            if target_face_feat is not None and crop_face_feat is not None:
                                face_sim = float((crop_face_feat @ target_face_feat.T).squeeze())
                                body_sim = float((crop_feat @ target_feat.T).squeeze())
                                # Weight face match heavily (70% face, 30% body)
                                best_score = max(best_score, 0.7 * face_sim + 0.3 * body_sim)
                            else:
                                # Fallback: full-body comparison
                                img_sim = float((crop_feat @ target_feat.T).squeeze())
                                best_score = max(best_score, img_sim)

                        # Score against text prompts (facial attribute mode)
                        if text_feats is not None:
                            text_sims = (crop_feat @ text_feats.T).squeeze()
                            text_score = float(text_sims.max() if text_sims.dim() > 0 else text_sims)
                            # Blend: if both image and text, average. If text only, use text.
                            if target_feat is not None:
                                best_score = 0.6 * best_score + 0.4 * text_score
                            else:
                                best_score = text_score

                        # Step 4: Record match if above threshold
                        if best_score >= SIMILARITY_THRESHOLD:
                            # ── CLIP dedup: check if this person was already matched ──
                            # Compare this crop's CLIP embedding against all existing
                            # match embeddings. If similarity > DEDUP_SIM, it's the
                            # same person — keep the one with higher score.
                            is_duplicate = False
                            dup_idx = -1
                            for mi, mf in enumerate(match_feats):
                                sim = float((crop_feat @ mf.T).squeeze())
                                if sim > DEDUP_SIM:
                                    is_duplicate = True
                                    dup_idx = mi
                                    break

                            if is_duplicate and dup_idx >= 0:
                                # Same person — keep better match
                                if best_score > matches[dup_idx]["confidence"]:
                                    # Replace with this better match
                                    pass  # fall through to overwrite
                                else:
                                    continue  # existing match is better, skip

                            # Draw bbox on FULL FRAME for thumbnail
                            thumb_frame = frame.copy()
                            cv2.rectangle(thumb_frame, (x1, y1), (x2, y2), (57, 255, 20), 3)
                            cv2.putText(thumb_frame, f"{best_score:.0%} MATCH",
                                        (x1, max(y1 - 8, 16)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (57, 255, 20), 2)
                            # Resize to reasonable thumbnail size
                            thumb_h = 200
                            thumb_w = int(thumb_h * w_frame / h_frame)
                            thumb_frame = cv2.resize(thumb_frame, (thumb_w, thumb_h))

                            _, buf = cv2.imencode(
                                ".jpg", thumb_frame,
                                [cv2.IMWRITE_JPEG_QUALITY, 75]
                            )
                            thumb_b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode()

                            match_data = {
                                "timestamp":   round(timestamp, 2),
                                "confidence":  round(best_score, 3),
                                "description": (
                                    f"Person detected at "
                                    f"{int(timestamp//60):02d}:{int(timestamp%60):02d} "
                                    f"— similarity {best_score:.0%}"
                                ),
                                "thumbnail":   thumb_b64,
                            }

                            if is_duplicate and dup_idx >= 0:
                                # Overwrite existing weaker match
                                matches[dup_idx] = match_data
                                match_feats[dup_idx] = crop_feat
                            else:
                                matches.append(match_data)
                                match_feats.append(crop_feat)

            frame_idx += 1

        cap.release()
    finally:
        if tmp_video:
            try: os.unlink(tmp_video.name)
            except: pass

    # Sort by confidence descending and cap to MAX_MATCHES
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    matches = matches[:MAX_MATCHES]

    # Clean up match_feats from GPU memory
    del match_feats

    return {
        "matches": matches,
        "total_scanned": frame_idx,
        "threshold": SIMILARITY_THRESHOLD,
        "search_mode": search_mode,
    }


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

    # Write initial progress immediately so frontend doesn't see 0%
    db.execute(
        text("UPDATE analyses SET description='||PROGRESS||1||MSG||Uploading complete. Queuing AI pipeline...' WHERE id=:id"),
        {"id": analysis_id}
    )
    db.commit()

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

    # Progress written as '||PROGRESS||NN||MSG||text'
    progress = 0
    live_msg = ""
    if row.description and "||PROGRESS||" in row.description:
        try:
            after_prog = row.description.split("||PROGRESS||")[-1]
            if "||MSG||" in after_prog:
                parts = after_prog.split("||MSG||")
                progress = int(parts[0])
                live_msg = parts[1] if len(parts) > 1 else ""
            else:
                progress = int(after_prog)
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
        "live_msg": live_msg,
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
