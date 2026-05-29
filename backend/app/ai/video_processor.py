"""
SkyRecon – Core AI Video Processing Engine
Handles frame extraction, YOLOv8 inference, and result persistence.
"""

import cv2
import os
import time
import uuid
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from ultralytics import YOLO
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.config import settings

logger = logging.getLogger(__name__)

# ── YOLO class-name → SkyRecon category mapping ──────────────────────────────
# Maps YOLO's 80 COCO class names to our 25 platform categories.
YOLO_TO_CATEGORY: dict[str, str] = {
    # Vehicles
    "car": "Vehicles", "truck": "Vehicles", "bus": "Vehicles",
    "motorcycle": "Vehicles", "bicycle": "Vehicles",
    "boat": "Vehicles", "train": "Railway Tracks",
    "airplane": "Vehicles",
    # People
    "person": "People",
    # Animals
    "cat": "Animals", "dog": "Animals", "horse": "Animals",
    "cow": "Animals", "sheep": "Animals", "bird": "Animals",
    "elephant": "Animals", "bear": "Animals", "zebra": "Animals",
    "giraffe": "Animals",
    # Infrastructure
    "traffic light": "Traffic Lights",
    "fire hydrant": "Buildings",
    "stop sign": "Roads",
    "bench": "Buildings",
    "chair": "Buildings",
    "couch": "Buildings",
    "bed": "Houses",
    "dining table": "Buildings",
    "toilet": "Buildings",
    "tv": "Buildings",
    "laptop": "Buildings",
    "cell phone": "People",
    "bottle": "Garbage Areas",
    "cup": "Garbage Areas",
    "fork": "Garbage Areas",
    "knife": "Garbage Areas",
    "spoon": "Garbage Areas",
    "bowl": "Garbage Areas",
    "banana": "Plants",
    "apple": "Plants",
    "orange": "Plants",
    "broccoli": "Plants",
    "carrot": "Plants",
    "potted plant": "Plants",
    "vase": "Buildings",
    "backpack": "People",
    "umbrella": "People",
    "handbag": "People",
    "tie": "People",
    "suitcase": "People",
    "frisbee": "People",
    "skis": "People",
    "snowboard": "People",
    "sports ball": "People",
    "kite": "People",
    "baseball bat": "People",
    "baseball glove": "People",
    "skateboard": "People",
    "surfboard": "People",
    "tennis racket": "People",
    "wine glass": "Garbage Areas",
    "hot dog": "Garbage Areas",
    "pizza": "Garbage Areas",
    "donut": "Garbage Areas",
    "cake": "Garbage Areas",
    "keyboard": "Buildings",
    "mouse": "Buildings",
    "remote": "Buildings",
    "microwave": "Buildings",
    "oven": "Buildings",
    "toaster": "Buildings",
    "sink": "Buildings",
    "refrigerator": "Buildings",
    "book": "Buildings",
    "clock": "Buildings",
    "scissors": "Buildings",
    "teddy bear": "People",
    "hair drier": "Buildings",
    "toothbrush": "Buildings",
}

# Disaster-relevant YOLO classes for the disaster engine
DISASTER_CLASSES = {"fire", "smoke", "flood", "person"}

# How many frames to sample per second of video (balance speed vs accuracy)
FRAMES_PER_SECOND = 2


def _get_or_create_category_id(db: Session, category_name: str) -> Optional[int]:
    """Returns the DB id for a category name, or None if not found."""
    result = db.execute(
        text("SELECT id FROM categories WHERE name = :name AND active = TRUE"),
        {"name": category_name}
    ).first()
    return result.id if result else None


def _save_screenshot(frame: np.ndarray, prefix: str) -> str:
    """Saves a frame as a JPEG screenshot and returns the relative path."""
    os.makedirs(settings.SCREENSHOTS_DIR, exist_ok=True)
    filename = f"{prefix}_{uuid.uuid4().hex[:8]}.jpg"
    filepath = os.path.join(settings.SCREENSHOTS_DIR, filename)
    cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return f"/screenshots/{filename}"


def _draw_detections(frame: np.ndarray, boxes, names: dict) -> np.ndarray:
    """Draws bounding boxes and labels on a frame copy."""
    annotated = frame.copy()
    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = f"{names[cls_id]} {conf:.0%}"
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (57, 255, 20), 2)
        cv2.putText(annotated, label, (x1, y1 - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (57, 255, 20), 1)
    return annotated


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
    Main mapping analysis pipeline.
    1. Load YOLOv8 model
    2. Extract frames from video at FRAMES_PER_SECOND rate
    3. Run inference on each frame
    4. Filter by selected_category
    5. Persist detections to DB via stored procedure
    6. Return summary stats
    """
    start_time = time.time()
    logger.info(f"[AI] Starting mapping analysis {analysis_id} | mode={detection_mode}")

    # Mark as processing
    db.execute(
        text("UPDATE analyses SET status='processing' WHERE id=:id"),
        {"id": analysis_id}
    )
    db.commit()

    try:
        model = YOLO(settings.YOLO_MODEL)
        model.fuse()  # fuse Conv+BN layers for faster inference

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(fps / FRAMES_PER_SECOND))

        logger.info(f"[AI] Video: {total_frames} frames @ {fps:.1f}fps, sampling every {frame_interval} frames")

        detection_count = 0
        frame_idx = 0
        processed_frames = 0

        # Category filter: which YOLO classes map to the selected category
        target_category = selected_category.strip()
        target_yolo_classes = {
            cls for cls, cat in YOLO_TO_CATEGORY.items()
            if cat.lower() == target_category.lower()
        }

        # For custom mode, use all classes (YOLO-World would be used in production)
        if detection_mode == "custom":
            target_yolo_classes = set(YOLO_TO_CATEGORY.keys())

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp_sec = frame_idx / fps
                results = model(frame, verbose=False, conf=settings.CONFIDENCE_THRESHOLD)

                for result in results:
                    if result.boxes is None:
                        continue
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        cls_name = model.names[cls_id]
                        confidence = float(box.conf[0])

                        # Filter to target category
                        mapped_cat = YOLO_TO_CATEGORY.get(cls_name)
                        if not mapped_cat:
                            continue
                        if detection_mode != "custom" and mapped_cat.lower() != target_category.lower():
                            continue

                        # Get category id from DB
                        cat_id = _get_or_create_category_id(db, mapped_cat)
                        if cat_id is None:
                            continue

                        # Bounding box (normalized 0-1)
                        h, w = frame.shape[:2]
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        bbox_x = x1 / w
                        bbox_y = y1 / h
                        bbox_w = (x2 - x1) / w
                        bbox_h = (y2 - y1) / h

                        # Save annotated screenshot every 50 detections to avoid disk bloat
                        screenshot_path = None
                        if detection_count % 50 == 0:
                            annotated = _draw_detections(frame, result.boxes, model.names)
                            screenshot_path = _save_screenshot(annotated, f"map_{analysis_id}")

                        # Persist via stored procedure
                        db.execute(
                            text("""
                                SELECT record_detection(
                                    :analysis_id, :category_id, :label, :confidence,
                                    :bbox_x, :bbox_y, :bbox_w, :bbox_h,
                                    :frame_number, :timestamp, NULL, NULL,
                                    :characteristics::jsonb
                                )
                            """),
                            {
                                "analysis_id": analysis_id,
                                "category_id": cat_id,
                                "label": f"{cls_name} ({confidence:.0%})",
                                "confidence": confidence,
                                "bbox_x": bbox_x,
                                "bbox_y": bbox_y,
                                "bbox_w": bbox_w,
                                "bbox_h": bbox_h,
                                "frame_number": frame_idx,
                                "timestamp": timestamp_sec,
                                "characteristics": str(characteristics).replace("'", '"'),
                            }
                        )
                        detection_count += 1

                processed_frames += 1
                # Commit every 100 processed frames to avoid huge transactions
                if processed_frames % 100 == 0:
                    db.commit()

            frame_idx += 1

        cap.release()
        db.commit()

        processing_time = time.time() - start_time

        # Mark complete via stored procedure
        db.execute(
            text("SELECT complete_analysis(:id, :total, :time)"),
            {"id": analysis_id, "total": detection_count, "time": processing_time}
        )
        db.commit()

        logger.info(f"[AI] Mapping analysis {analysis_id} complete: {detection_count} detections in {processing_time:.1f}s")
        return {
            "analysis_id": analysis_id,
            "total_detections": detection_count,
            "processing_time": processing_time,
            "frames_processed": processed_frames,
        }

    except Exception as e:
        logger.error(f"[AI] Mapping analysis {analysis_id} FAILED: {e}")
        db.execute(
            text("UPDATE analyses SET status='failed' WHERE id=:id"),
            {"id": analysis_id}
        )
        db.commit()
        raise
