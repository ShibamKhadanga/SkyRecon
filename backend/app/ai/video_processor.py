"""
SkyRecon – Core AI Video Processing Engine
Uses YOLOv8 + ByteTrack for accurate unique object counting.

KEY IMPROVEMENT:
  Old approach: IoU dedup between adjacent frames → same person counted 10-30x
  New approach: ByteTrack assigns each unique object a persistent ID across the
                ENTIRE video. Person walks through whole video = 1 unique ID = counted once.
  ByteTrack is built into Ultralytics — no extra install needed.
"""

import cv2
import os
import time
import uuid
import json
import logging
from typing import Optional

import numpy as np
from ultralytics import YOLO
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.config import settings

logger = logging.getLogger(__name__)

# ── Model cache — load once per process, reuse across all analyses ────────────
_model_cache: dict[str, YOLO] = {}

def _get_model(model_path: str) -> YOLO:
    if model_path not in _model_cache:
        logger.info(f"[AI] Loading model: {model_path}")
        m = YOLO(model_path)
        m.fuse()
        _model_cache[model_path] = m
        logger.info(f"[AI] Model ready.")
    return _model_cache[model_path]


# ── YOLO COCO class → SkyRecon category ──────────────────────────────────────
YOLO_TO_CATEGORY: dict[str, str] = {
    "car": "Vehicles", "truck": "Vehicles", "bus": "Vehicles",
    "motorcycle": "Vehicles", "bicycle": "Vehicles",
    "boat": "Vehicles", "train": "Railway Tracks", "airplane": "Vehicles",
    "person": "People",
    "cat": "Animals", "dog": "Animals", "horse": "Animals",
    "cow": "Animals", "sheep": "Animals", "bird": "Animals",
    "elephant": "Animals", "bear": "Animals", "zebra": "Animals",
    "giraffe": "Animals",
    "traffic light": "Traffic Lights",
    "fire hydrant": "Electric Poles",
    "stop sign": "Roads",
    "bench": "Buildings", "chair": "Buildings", "couch": "Buildings",
    "bed": "Houses", "dining table": "Buildings",
    "tv": "Buildings", "laptop": "Buildings", "cell phone": "People",
    "bottle": "Garbage Areas", "cup": "Garbage Areas",
    "potted plant": "Plants",
    "vase": "Buildings", "backpack": "People", "umbrella": "People",
    "handbag": "People", "tie": "People", "suitcase": "People",
    "sports ball": "People", "kite": "People",
    "skateboard": "People", "surfboard": "People",
    "wine glass": "Garbage Areas",
    "keyboard": "Buildings", "mouse": "Buildings",
    "clock": "Buildings", "teddy bear": "People",
}

# ── Per-category inference config ─────────────────────────────────────────────
# People from aerial view need lower confidence + higher fps to catch walkers
CATEGORY_SETTINGS: dict[str, dict] = {
    "people":       {"fps": 2, "conf": 0.28, "iou": 0.40},
    "vehicles":     {"fps": 1, "conf": 0.38, "iou": 0.50},
    "animals":      {"fps": 1, "conf": 0.32, "iou": 0.45},
    "fire & smoke": {"fps": 2, "conf": 0.28, "iou": 0.40},
    "flood water":  {"fps": 1, "conf": 0.32, "iou": 0.50},
    "default":      {"fps": 1, "conf": 0.38, "iou": 0.50},
}

FRAMES_PER_SECOND = 1   # fallback
MAX_SCREENSHOTS   = 8


# ── Frame enhancement ─────────────────────────────────────────────────────────
def _enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    CLAHE contrast enhancement for drone footage.
    Drone footage is often hazy/washed-out from altitude.
    Enhancing local contrast makes people and objects more distinct.
    """
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    # Mild sharpening
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
    return cv2.addWeighted(enhanced, 1.4, blurred, -0.4, 0)


# ── DB helpers ────────────────────────────────────────────────────────────────
def _build_category_cache(db: Session) -> dict[str, int]:
    rows = db.execute(
        text("SELECT id, name FROM categories WHERE active = TRUE")
    ).fetchall()
    return {row.name: row.id for row in rows}


def _write_progress(db: Session, analysis_id: int, pct: int, count: int):
    db.execute(
        text("""
            UPDATE analyses
            SET total_objects = :count,
                description = CONCAT(
                    COALESCE(SPLIT_PART(COALESCE(description,''), '||PROGRESS||', 1), ''),
                    '||PROGRESS||', CAST(:pct AS TEXT)
                )
            WHERE id = :id
        """),
        {"id": analysis_id, "count": count, "pct": pct}
    )
    db.commit()


def _save_screenshot(frame: np.ndarray, prefix: str, timestamp_sec: float) -> str:
    os.makedirs(settings.SCREENSHOTS_DIR, exist_ok=True)
    filename = f"{prefix}_{uuid.uuid4().hex[:6]}.jpg"
    filepath = os.path.join(settings.SCREENSHOTS_DIR, filename)
    cv2.putText(frame, f"T={timestamp_sec:.1f}s",
                (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (57, 255, 20), 2)
    cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
    return f"/screenshots/{filename}"


# ── Main pipeline ─────────────────────────────────────────────────────────────
def run_mapping_analysis(
    analysis_id: int,
    video_path: str,
    selected_category: str,
    characteristics: dict,
    detection_mode: str,
    custom_query: str,
    db: Session,
) -> dict:
    """
    Full mapping pipeline with ByteTrack persistent tracking.

    How unique counting works:
    - model.track() runs ByteTrack internally on every sampled frame
    - Each unique object gets a persistent track_id (e.g. person #1, person #2)
    - We keep a set of all track_ids seen across the whole video
    - Final count = len(seen_track_ids) = true unique object count
    - A person walking through the entire video = 1 track_id = counted once
    """
    start_time = time.time()
    logger.info(f"[AI] Mapping {analysis_id} | category={selected_category}")

    db.execute(text("UPDATE analyses SET status='processing' WHERE id=:id"), {"id": analysis_id})
    db.commit()

    try:
        cat_key = selected_category.strip().lower()
        cat_cfg = CATEGORY_SETTINGS.get(cat_key, CATEGORY_SETTINGS["default"])
        fps_sample    = cat_cfg["fps"]
        conf_threshold = cat_cfg["conf"]
        iou_threshold  = cat_cfg["iou"]
        logger.info(f"[AI] Config: fps={fps_sample}, conf={conf_threshold}")

        model      = _get_model(settings.YOLO_MODEL)
        cat_cache  = _build_category_cache(db)
        chars_str  = json.dumps(characteristics)
        target_cat = selected_category.strip()

        is_image = video_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))

        if is_image:
            frame = cv2.imread(video_path)
            if frame is None:
                raise RuntimeError(f"Cannot read image: {video_path}")
            total_frames   = 1
            frame_interval = 1
            fps            = 1.0
        else:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise RuntimeError(f"Cannot open: {video_path}")
            fps            = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames   = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_interval = max(1, int(fps / fps_sample))
            logger.info(f"[AI] {total_frames} frames @ {fps:.1f}fps, interval={frame_interval}")

        # ── Tracking state ──
        # seen_track_ids: maps (track_id, cls_id) → first_seen_timestamp
        # This is the ground truth for unique object count
        seen_track_ids: dict[tuple, float] = {}

        batch: list[dict] = []
        BATCH_SIZE = 50
        raw_detection_count = 0
        screenshot_count = 0
        last_progress = 0

        def flush_batch():
            nonlocal raw_detection_count
            for det in batch:
                db.execute(
                    text("""
                        SELECT record_detection(
                            :analysis_id, :category_id, :label, :confidence,
                            :bbox_x, :bbox_y, :bbox_w, :bbox_h,
                            :frame_number, :timestamp, NULL, NULL,
                            CAST(:characteristics AS jsonb)
                        )
                    """),
                    det
                )
                raw_detection_count += 1
            db.commit()
            batch.clear()

        def process_frame(frame: np.ndarray, frame_idx: int, timestamp_sec: float):
            nonlocal screenshot_count

            h, w = frame.shape[:2]
            enhanced = _enhance_frame(frame)

            # Resize to 640px for speed
            if w > 640:
                scale = 640 / w
                frame_small = cv2.resize(enhanced, (640, int(h * scale)))
            else:
                frame_small = enhanced
            h_s, w_s = frame_small.shape[:2]

            # ── ByteTrack tracking ──
            # model.track() runs detection + ByteTrack in one call.
            # Each box gets a .id (persistent track ID across frames).
            # persist=True keeps the tracker state between calls.
            try:
                results = model.track(
                    frame_small,
                    persist=True,           # keep tracker state across frames
                    verbose=False,
                    conf=conf_threshold,
                    iou=iou_threshold,
                    agnostic_nms=True,
                    max_det=300,
                    tracker="bytetrack.yaml",  # ByteTrack config (built into ultralytics)
                )
            except Exception:
                # Fallback to plain detection if tracker fails
                results = model(
                    frame_small,
                    verbose=False,
                    conf=conf_threshold,
                    iou=iou_threshold,
                    agnostic_nms=True,
                    max_det=300,
                )

            screenshot_saved = False

            for result in results:
                if result.boxes is None or len(result.boxes) == 0:
                    continue

                # Draw annotated screenshot
                if not screenshot_saved and screenshot_count < MAX_SCREENSHOTS:
                    annotated = frame.copy()

                for box in result.boxes:
                    cls_id     = int(box.cls[0])
                    cls_name   = model.names[cls_id]
                    confidence = float(box.conf[0])

                    # Get ByteTrack ID — None if tracker didn't assign one
                    track_id = int(box.id[0]) if box.id is not None else None

                    mapped_cat = YOLO_TO_CATEGORY.get(cls_name)
                    if not mapped_cat:
                        continue
                    if detection_mode != "custom" and mapped_cat.lower() != target_cat.lower():
                        continue

                    cat_id = cat_cache.get(mapped_cat)
                    if cat_id is None:
                        continue

                    # Scale bbox back to original resolution
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    x1o = x1 * (w / w_s); y1o = y1 * (h / h_s)
                    x2o = x2 * (w / w_s); y2o = y2 * (h / h_s)

                    # ── Unique object tracking ──
                    # Key = (track_id, cls_id) — unique per object type
                    # If track_id is None (fallback), use bbox hash as key
                    if track_id is not None:
                        obj_key = (track_id, cls_id)
                    else:
                        # Fallback: round bbox to nearest 20px to group same object
                        obj_key = (round(x1o/20), round(y1o/20), round(x2o/20), round(y2o/20), cls_id)

                    is_first_appearance = obj_key not in seen_track_ids

                    if is_first_appearance:
                        seen_track_ids[obj_key] = timestamp_sec
                        # Only save to DB on FIRST appearance
                        label = (
                            f"{cls_name} #{track_id if track_id else 'new'} "
                            f"({confidence:.0%}) first seen T={timestamp_sec:.1f}s"
                        )
                        batch.append({
                            "analysis_id": analysis_id,
                            "category_id": cat_id,
                            "label": label,
                            "confidence": confidence,
                            "bbox_x": x1o / w, "bbox_y": y1o / h,
                            "bbox_w": (x2o - x1o) / w,
                            "bbox_h": (y2o - y1o) / h,
                            "frame_number": frame_idx,
                            "timestamp": timestamp_sec,
                            "characteristics": chars_str,
                        })

                    # Draw on screenshot regardless
                    if not screenshot_saved and screenshot_count < MAX_SCREENSHOTS:
                        bx1, by1, bx2, by2 = map(int, [x1o, y1o, x2o, y2o])
                        color = (57, 255, 20) if is_first_appearance else (0, 200, 255)
                        cv2.rectangle(annotated, (bx1, by1), (bx2, by2), color, 2)
                        tid_str = f"#{track_id}" if track_id else ""
                        cv2.putText(annotated,
                                    f"{cls_name}{tid_str} {confidence:.0%}",
                                    (bx1, max(by1 - 6, 10)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

                if not screenshot_saved and screenshot_count < MAX_SCREENSHOTS:
                    _save_screenshot(annotated, f"map_{analysis_id}", timestamp_sec)
                    screenshot_count += 1
                    screenshot_saved = True

            if len(batch) >= BATCH_SIZE:
                flush_batch()

        # ── Main loop ──
        if is_image:
            process_frame(frame, 0, 0.0)
            flush_batch()
            _write_progress(db, analysis_id, 100, len(seen_track_ids))
        else:
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_interval == 0:
                    process_frame(frame, frame_idx, frame_idx / fps)

                    if total_frames > 0:
                        pct = min(99, int((frame_idx / total_frames) * 100))
                        if pct >= last_progress + 5:
                            flush_batch()
                            _write_progress(db, analysis_id, pct, len(seen_track_ids))
                            last_progress = pct
                            logger.info(
                                f"[AI] {pct}% | {len(seen_track_ids)} unique objects tracked"
                            )

                frame_idx += 1

            cap.release()
            flush_batch()

        processing_time = time.time() - start_time
        unique_count = len(seen_track_ids)

        db.execute(
            text("SELECT complete_analysis(:id, :total, :time)"),
            {"id": analysis_id, "total": unique_count, "time": processing_time}
        )
        db.commit()

        logger.info(
            f"[AI] Done: {unique_count} unique objects "
            f"({raw_detection_count} raw detections) in {processing_time:.1f}s"
        )
        return {
            "analysis_id":      analysis_id,
            "total_detections": unique_count,
            "raw_detections":   raw_detection_count,
            "unique_objects":   unique_count,
            "processing_time":  processing_time,
        }

    except Exception as e:
        logger.error(f"[AI] Mapping FAILED {analysis_id}: {e}", exc_info=True)
        db.execute(text("UPDATE analyses SET status='failed' WHERE id=:id"), {"id": analysis_id})
        db.commit()
        raise


def run_image_analysis(
    analysis_id: int,
    image_path: str,
    selected_category: str,
    characteristics: dict,
    detection_mode: str,
    db: Session,
) -> dict:
    return run_mapping_analysis(
        analysis_id=analysis_id,
        video_path=image_path,
        selected_category=selected_category,
        characteristics=characteristics,
        detection_mode=detection_mode,
        custom_query="",
        db=db,
    )
