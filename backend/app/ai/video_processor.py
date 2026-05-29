"""
SkyRecon – Core AI Video Processing Engine
Handles frame extraction, YOLOv8 inference, and result persistence.
Optimised for speed: category cache, batch inserts, real progress tracking.
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

# ── Pre-load YOLO model once at module level (avoids reloading per analysis) ──
_model_cache: dict = {}

def _get_model(model_path: str):
    """Load and cache YOLO model — only loads once per process."""
    if model_path not in _model_cache:
        logger.info(f"[AI] Loading YOLO model: {model_path}")
        m = YOLO(model_path)
        m.fuse()
        _model_cache[model_path] = m
        logger.info(f"[AI] Model loaded and fused.")
    return _model_cache[model_path]

# ── YOLO class-name → SkyRecon category mapping ──────────────────────────────
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
    # fire hydrant is a vertical pole-like structure — map to Electric Poles
    "fire hydrant": "Electric Poles",
    "stop sign": "Roads",
    "parking meter": "Electric Poles",  # vertical pole structure
    "bench": "Buildings", "chair": "Buildings", "couch": "Buildings",
    "bed": "Houses", "dining table": "Buildings", "toilet": "Buildings",
    "tv": "Buildings", "laptop": "Buildings", "cell phone": "People",
    "bottle": "Garbage Areas", "cup": "Garbage Areas",
    "fork": "Garbage Areas", "knife": "Garbage Areas",
    "spoon": "Garbage Areas", "bowl": "Garbage Areas",
    "banana": "Plants", "apple": "Plants", "orange": "Plants",
    "broccoli": "Plants", "carrot": "Plants", "potted plant": "Plants",
    "vase": "Buildings", "backpack": "People", "umbrella": "People",
    "handbag": "People", "tie": "People", "suitcase": "People",
    "frisbee": "People", "skis": "People", "snowboard": "People",
    "sports ball": "People", "kite": "People", "baseball bat": "People",
    "baseball glove": "People", "skateboard": "People",
    "surfboard": "People", "tennis racket": "People",
    "wine glass": "Garbage Areas", "hot dog": "Garbage Areas",
    "pizza": "Garbage Areas", "donut": "Garbage Areas",
    "cake": "Garbage Areas", "keyboard": "Buildings", "mouse": "Buildings",
    "remote": "Buildings", "microwave": "Buildings", "oven": "Buildings",
    "toaster": "Buildings", "sink": "Buildings",
    "refrigerator": "Buildings", "book": "Buildings", "clock": "Buildings",
    "scissors": "Buildings", "teddy bear": "People",
    "hair drier": "Buildings", "toothbrush": "Buildings",
}

# ── Pole-like structures: YOLOv8 doesn’t have a “pole” class.
# We detect them by their tall narrow bounding-box aspect ratio (height >> width).
# Any detection with aspect ratio > POLE_ASPECT_RATIO is reclassified as a pole.
POLE_ASPECT_RATIO = 3.5   # height/width > 3.5 → likely a pole/post
POLE_MIN_CONF    = 0.30   # lower threshold since poles are hard to detect

# ── Per-category inference settings ─────────────────────────────────────────
# Different categories need different sampling rates and confidence thresholds.
# People from aerial view are harder to detect — lower conf, higher fps.
CATEGORY_SETTINGS: dict[str, dict] = {
    "people":          {"fps": 2, "conf": 0.30, "iou": 0.45},
    "vehicles":        {"fps": 1, "conf": 0.40, "iou": 0.50},
    "animals":         {"fps": 1, "conf": 0.35, "iou": 0.45},
    "fire & smoke":    {"fps": 2, "conf": 0.30, "iou": 0.40},
    "flood water":     {"fps": 1, "conf": 0.35, "iou": 0.50},
    "default":         {"fps": 1, "conf": 0.40, "iou": 0.50},
}

# Default fallback
FRAMES_PER_SECOND = 1
MAX_SCREENSHOTS = 8


def _build_category_cache(db: Session) -> dict[str, int]:
    """Load all active categories into memory once — avoids per-detection DB calls."""
    rows = db.execute(
        text("SELECT id, name FROM categories WHERE active = TRUE")
    ).fetchall()
    return {row.name: row.id for row in rows}


def _enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to improve
    detection accuracy on drone footage which is often hazy, washed-out, or
    low-contrast from altitude.
    Also sharpens slightly to make edges (people, vehicles) more distinct.
    """
    # Convert to LAB color space — apply CLAHE only to L (luminance) channel
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)

    # CLAHE: clipLimit controls contrast boost, tileGridSize controls locality
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l)

    # Merge back and convert to BGR
    enhanced = cv2.merge([l_enhanced, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    # Mild unsharp mask for edge sharpening
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
    sharpened = cv2.addWeighted(enhanced, 1.4, blurred, -0.4, 0)

    return sharpened


class _DetectionDeduplicator:
    """
    Persistent object tracker across ALL frames (not just adjacent).
    Each unique object gets an ID. A detection is "new" only if it doesn't
    overlap with ANY previously tracked object above the IoU threshold.
    Tracks objects until they leave the frame (no match for >5 sampled frames).
    This prevents the same person being counted 30+ times as they walk across.
    """
    def __init__(self, iou_threshold: float = 0.40, max_missing: int = 5):
        self.iou_threshold = iou_threshold
        self.max_missing = max_missing  # frames before dropping a track
        # tracked_objects: list of {box:(x1,y1,x2,y2), cls:int, missing:int}
        self.tracked: list[dict] = []
        self.unique_count = 0

    def _iou(self, a: tuple, b: tuple) -> float:
        ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
        ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        if inter == 0:
            return 0.0
        union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
        return inter / union if union > 0 else 0.0

    def process_frame(self, detections: list[tuple]) -> list[bool]:
        """
        Takes list of (x1,y1,x2,y2,cls_id) for current frame.
        Returns list of booleans — True means this detection is a NEW unique object.
        Updates internal tracks.
        """
        matched_track_ids = set()
        is_new_flags = []

        for det in detections:
            x1, y1, x2, y2, cls_id = det
            best_iou = 0.0
            best_idx = -1
            for i, track in enumerate(self.tracked):
                if track["cls"] != cls_id:
                    continue
                iou = self._iou((x1, y1, x2, y2), track["box"])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = i

            if best_iou >= self.iou_threshold and best_idx >= 0:
                # Matched existing track — update position, NOT a new object
                self.tracked[best_idx]["box"] = (x1, y1, x2, y2)
                self.tracked[best_idx]["missing"] = 0
                matched_track_ids.add(best_idx)
                is_new_flags.append(False)
            else:
                # Genuinely new object never seen before
                self.tracked.append({"box": (x1, y1, x2, y2), "cls": cls_id, "missing": 0})
                matched_track_ids.add(len(self.tracked) - 1)
                self.unique_count += 1
                is_new_flags.append(True)

        # Age unmatched tracks — drop if missing too long
        for i, track in enumerate(self.tracked):
            if i not in matched_track_ids:
                track["missing"] += 1
        self.tracked = [t for t in self.tracked if t["missing"] <= self.max_missing]

        return is_new_flags

    # Keep backward-compat shims
    def is_new(self, x1, y1, x2, y2, cls_id):
        return True  # not used in new flow

    def update(self, boxes):
        pass  # not used in new flow


def _save_screenshot(frame: np.ndarray, prefix: str, timestamp_sec: float) -> str:
    """Saves an annotated frame as JPEG with timestamp burned in."""
    os.makedirs(settings.SCREENSHOTS_DIR, exist_ok=True)
    filename = f"{prefix}_{uuid.uuid4().hex[:6]}.jpg"
    filepath = os.path.join(settings.SCREENSHOTS_DIR, filename)

    # Burn timestamp onto frame
    ts_label = f"T={timestamp_sec:.1f}s"
    cv2.putText(frame, ts_label, (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (57, 255, 20), 2)
    cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return f"/screenshots/{filename}"


def _draw_and_save(frame: np.ndarray, boxes, names: dict,
                   prefix: str, timestamp_sec: float) -> str:
    """Draw bounding boxes + timestamp on frame and save."""
    annotated = frame.copy()
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = f"{names[cls_id]} {conf:.0%}"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (57, 255, 20), 2)
        cv2.putText(annotated, label, (x1, max(y1 - 6, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (57, 255, 20), 1)
    return _save_screenshot(annotated, prefix, timestamp_sec)


def _write_progress(db: Session, analysis_id: int, pct: int, count: int):
    """Write real-time progress into the DB so the frontend can read it."""
    db.execute(
        text("""
            UPDATE analyses
            SET total_objects = :count,
                description = CONCAT(
                    COALESCE(SPLIT_PART(COALESCE(description, ''), '||PROGRESS||', 1), ''),
                    '||PROGRESS||', CAST(:pct AS TEXT)
                )
            WHERE id = :id
        """),
        {"id": analysis_id, "count": count, "pct": pct}
    )
    db.commit()


def run_mapping_analysis(
    analysis_id: int,
    video_path: str,
    selected_category: str,
    characteristics: dict,
    detection_mode: str,
    custom_query: str,
    db: Session,
) -> dict:
    start_time = time.time()
    logger.info(f"[AI] Mapping analysis {analysis_id} | category={selected_category}")

    db.execute(text("UPDATE analyses SET status='processing' WHERE id=:id"), {"id": analysis_id})
    db.commit()

    try:
        # ── Per-category settings ──
        cat_key = selected_category.strip().lower()
        cat_cfg = CATEGORY_SETTINGS.get(cat_key, CATEGORY_SETTINGS["default"])
        fps_sample = cat_cfg["fps"]
        conf_threshold = cat_cfg["conf"]
        iou_threshold = cat_cfg["iou"]
        logger.info(f"[AI] Category config: fps={fps_sample}, conf={conf_threshold}, iou={iou_threshold}")

        # ── Load model (cached — only loads once per process) ──
        model = _get_model(settings.YOLO_MODEL)

        # ── Load category cache once ──
        cat_cache = _build_category_cache(db)

        # ── Deduplicator (persistent tracker) ──
        dedup = _DetectionDeduplicator(iou_threshold=0.40, max_missing=5)

        # ── Open video or image ──
        is_image = video_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))

        if is_image:
            raw_frame = cv2.imread(video_path)
            if raw_frame is None:
                raise RuntimeError(f"Cannot read image: {video_path}")
            frames_to_process = [(raw_frame, 0, 0.0)]
            total_frames = 1
        else:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise RuntimeError(f"Cannot open file: {video_path}")
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_interval = max(1, int(fps / fps_sample))
            logger.info(f"[AI] {total_frames} frames @ {fps:.1f}fps, sampling every {frame_interval} frames")

        target_category = selected_category.strip()
        detection_count = 0
        frame_idx = 0
        screenshot_count = 0
        chars_str = json.dumps(characteristics)
        batch: list[dict] = []
        BATCH_SIZE = 50

        def flush_batch():
            nonlocal detection_count
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
                detection_count += 1
            db.commit()
            batch.clear()

        def process_frame(frame: np.ndarray, frame_idx: int, timestamp_sec: float):
            nonlocal screenshot_count

            h, w = frame.shape[:2]

            # Step 1: Enhance frame contrast for aerial footage
            enhanced = _enhance_frame(frame)

            # Step 2: Resize to 640px for faster inference
            if w > 640:
                scale = 640 / w
                frame_small = cv2.resize(enhanced, (640, int(h * scale)))
            else:
                frame_small = enhanced
            h_s, w_s = frame_small.shape[:2]

            # Step 3: Run inference
            results = model(
                frame_small,
                verbose=False,
                conf=conf_threshold,
                iou=0.45,
                agnostic_nms=True,
                max_det=300,
            )

            # Collect all valid detections for this frame
            frame_detections = []  # (x1_orig, y1_orig, x2_orig, y2_orig, cls_id, cls_name, confidence, mapped_cat)

            for result in results:
                if result.boxes is None or len(result.boxes) == 0:
                    continue
                for box in result.boxes:
                    cls_id   = int(box.cls[0])
                    cls_name = model.names[cls_id]
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    # Scale back to original resolution
                    x1o = x1 * (w / w_s); y1o = y1 * (h / h_s)
                    x2o = x2 * (w / w_s); y2o = y2 * (h / h_s)

                    # ── Pole detection via aspect ratio heuristic ──
                    # YOLOv8 has no "pole" class. Tall narrow objects are poles.
                    box_h = y2o - y1o
                    box_w = x2o - x1o
                    if box_w > 0 and (box_h / box_w) > POLE_ASPECT_RATIO and confidence >= POLE_MIN_CONF:
                        mapped_cat = "Electric Poles"
                    else:
                        mapped_cat = YOLO_TO_CATEGORY.get(cls_name)

                    if not mapped_cat:
                        continue

                    # Filter to target category (unless custom mode)
                    if detection_mode != "custom" and mapped_cat.lower() != target_category.lower():
                        continue

                    cat_id = cat_cache.get(mapped_cat)
                    if cat_id is None:
                        continue

                    frame_detections.append((x1o, y1o, x2o, y2o, cls_id, cls_name, confidence, mapped_cat, cat_id))

            if not frame_detections:
                dedup.process_frame([])  # age existing tracks
                return

            # Step 4: Run persistent tracker — returns True for each NEW unique object
            tracker_input = [(d[0], d[1], d[2], d[3], d[4]) for d in frame_detections]
            is_new_flags = dedup.process_frame(tracker_input)

            # Count objects per category visible in this frame (for label)
            cat_counts_this_frame: dict[str, int] = {}
            for d in frame_detections:
                cat_counts_this_frame[d[7]] = cat_counts_this_frame.get(d[7], 0) + 1

            # Step 5: Save screenshot on first frame with detections
            if screenshot_count < MAX_SCREENSHOTS:
                annotated = frame.copy()
                for d in frame_detections:
                    bx1, by1, bx2, by2 = map(int, [d[0], d[1], d[2], d[3]])
                    cv2.rectangle(annotated, (bx1, by1), (bx2, by2), (57, 255, 20), 2)
                    cv2.putText(annotated, f"{d[5]} {d[6]:.0%}",
                                (bx1, max(by1-6, 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (57, 255, 20), 1)
                _save_screenshot(annotated, f"map_{analysis_id}", timestamp_sec)
                screenshot_count += 1

            # Step 6: Only save NEW unique objects to DB — skip repeat appearances
            # This ensures the detections table has exactly one row per unique object,
            # with the timestamp of its FIRST appearance in the video.
            for d, is_new in zip(frame_detections, is_new_flags):
                if not is_new:
                    continue  # already counted this object in a previous frame
                x1o, y1o, x2o, y2o, cls_id, cls_name, confidence, mapped_cat, cat_id = d
                count_in_frame = cat_counts_this_frame.get(mapped_cat, 1)
                label = f"{cls_name} ({confidence:.0%}) — {count_in_frame} visible at T={timestamp_sec:.1f}s"
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

            if len(batch) >= BATCH_SIZE:
                flush_batch()

        # ── Main loop ──
        if is_image:
            process_frame(frames_to_process[0][0], 0, 0.0)
            flush_batch()
            _write_progress(db, analysis_id, 100, detection_count)
        else:
            last_progress = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_interval == 0:
                    timestamp_sec = frame_idx / fps
                    process_frame(frame, frame_idx, timestamp_sec)

                    if total_frames > 0:
                        pct = min(99, int((frame_idx / total_frames) * 100))
                        if pct >= last_progress + 5:  # write every 5% for smoother UI
                            flush_batch()
                            _write_progress(db, analysis_id, pct, detection_count)
                            last_progress = pct
                            logger.info(f"[AI] Progress: {pct}% | {detection_count} raw | {dedup.unique_count} unique")

                frame_idx += 1

            cap.release()
            flush_batch()

        processing_time = time.time() - start_time

        # Use the tracker's unique object count as the final total
        final_count = dedup.unique_count if dedup.unique_count > 0 else detection_count
        db.execute(
            text("SELECT complete_analysis(:id, :total, :time)"),
            {"id": analysis_id, "total": final_count, "time": processing_time}
        )
        db.commit()

        logger.info(
            f"[AI] Done: {detection_count} raw detections, "
            f"{dedup.unique_count} unique objects in {processing_time:.1f}s"
        )
        return {
            "analysis_id": analysis_id,
            "total_detections": final_count,
            "raw_detections": detection_count,
            "unique_detections": dedup.unique_count,
            "processing_time": processing_time,
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
    """Thin wrapper — images are just single-frame videos."""
    return run_mapping_analysis(
        analysis_id=analysis_id,
        video_path=image_path,
        selected_category=selected_category,
        characteristics=characteristics,
        detection_mode=detection_mode,
        custom_query="",
        db=db,
    )
