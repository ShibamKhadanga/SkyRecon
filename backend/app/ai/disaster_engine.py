"""
SkyRecon – Disaster Detection Engine
Classifies disaster events from drone video frames, assigns severity 1-5,
captures screenshots, and persists events via stored procedures.
"""

import cv2
import os
import time
import logging
from typing import Optional

import numpy as np
from ultralytics import YOLO
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.config import settings
from .video_processor import _save_screenshot, FRAMES_PER_SECOND

logger = logging.getLogger(__name__)

# ── Disaster type detection rules ────────────────────────────────────────────
# Each entry: YOLO class names that trigger this disaster type
DISASTER_TRIGGERS: dict[str, list[str]] = {
    "fire":       ["fire", "flame"],          # custom / fine-tuned classes
    "flood":      ["boat", "water"],           # boats in unexpected places = flood proxy
    "structural": ["building", "house"],       # detected with damage heuristic
    "people":     ["person"],                  # trapped people
    "vehicles":   ["car", "truck", "bus"],     # accident / blocked roads
    "trees":      ["tree"],                    # fallen trees (custom class)
    "poles":      ["pole"],                    # fallen poles (custom class)
}

# YOLO COCO classes that are relevant for disaster context
DISASTER_RELEVANT_CLASSES = {
    "person", "car", "truck", "bus", "motorcycle",
    "boat", "fire hydrant", "stop sign",
}

# Severity scoring weights
SEVERITY_WEIGHTS = {
    "fire":       5,
    "flood":      5,
    "structural": 4,
    "people":     4,
    "vehicles":   3,
    "trees":      2,
    "poles":      2,
}

DISASTER_RECOMMENDATIONS = {
    "fire": (
        "Deploy fire suppression units immediately. Evacuate all civilians within 500m radius. "
        "Alert fire department and ensure water supply lines are active."
    ),
    "flood": (
        "Initiate emergency evacuation of ground-floor residents. Deploy rescue boats. "
        "Activate flood relief camps. Alert NDRF teams for deep-water rescue."
    ),
    "structural": (
        "Cordon off the damaged structure. Deploy structural engineers for assessment. "
        "Evacuate adjacent buildings. Alert urban search and rescue teams."
    ),
    "people": (
        "Trapped civilians detected. Dispatch rescue teams immediately. "
        "Coordinate with medical teams for on-site triage."
    ),
    "vehicles": (
        "Road blockage or vehicle accident detected. Deploy traffic management and "
        "emergency response vehicles. Clear route for ambulances."
    ),
    "trees": (
        "Fallen trees blocking roads or structures. Deploy municipal clearance teams. "
        "Check for downed power lines before clearing."
    ),
    "poles": (
        "Fallen electric poles detected. Alert electricity board immediately. "
        "Cordon off area — live wire hazard. Do not approach without insulated equipment."
    ),
}


def _compute_severity(
    disaster_type: str,
    detection_count: int,
    avg_confidence: float,
    affected_area_ratio: float,
) -> int:
    """
    Computes severity level 1-5 based on:
    - Base weight of disaster type
    - Number of detections (density)
    - Confidence of detections
    - Proportion of frame area affected
    """
    base = SEVERITY_WEIGHTS.get(disaster_type, 2)

    # Density bonus: more detections = higher severity
    density_bonus = min(2, detection_count // 3)

    # Area bonus: if affected area > 30% of frame
    area_bonus = 1 if affected_area_ratio > 0.30 else 0

    # Confidence penalty: low confidence = reduce severity
    conf_factor = 0 if avg_confidence < 0.55 else (1 if avg_confidence > 0.75 else 0)

    severity = base + density_bonus + area_bonus - (1 - conf_factor)
    return max(1, min(5, int(severity)))


def _classify_frame_disaster(
    frame: np.ndarray,
    boxes,
    names: dict,
) -> list[dict]:
    """
    Given YOLO detections on a frame, returns a list of disaster events found.
    Each event: {type, confidence, bbox_area_ratio, count}
    """
    h, w = frame.shape[:2]
    frame_area = h * w

    # Accumulate detections per disaster type
    type_data: dict[str, dict] = {}

    for box in boxes:
        cls_id = int(box.cls[0])
        cls_name = names[cls_id].lower()
        confidence = float(box.conf[0])

        # Check which disaster type this class triggers
        matched_type = None
        for dtype, triggers in DISASTER_TRIGGERS.items():
            if cls_name in triggers:
                matched_type = dtype
                break

        # Also flag if it's a disaster-relevant COCO class in unusual density
        if matched_type is None and cls_name in DISASTER_RELEVANT_CLASSES:
            matched_type = "people" if cls_name == "person" else "vehicles"

        if matched_type is None:
            continue

        x1, y1, x2, y2 = box.xyxy[0].tolist()
        bbox_area = (x2 - x1) * (y2 - y1)
        area_ratio = bbox_area / frame_area

        if matched_type not in type_data:
            type_data[matched_type] = {"confidences": [], "area_ratio": 0.0, "count": 0}

        type_data[matched_type]["confidences"].append(confidence)
        type_data[matched_type]["area_ratio"] += area_ratio
        type_data[matched_type]["count"] += 1

    events = []
    for dtype, data in type_data.items():
        avg_conf = sum(data["confidences"]) / len(data["confidences"])
        events.append({
            "type": dtype,
            "confidence": avg_conf,
            "area_ratio": min(1.0, data["area_ratio"]),
            "count": data["count"],
        })

    return events


def run_disaster_analysis(
    analysis_id: int,
    video_path: str,
    db: Session,
) -> dict:
    """
    Main disaster analysis pipeline.
    1. Load YOLOv8 model
    2. Sample frames from video
    3. Classify disaster events per frame
    4. Deduplicate: only record an event if it persists across multiple frames
    5. Assign severity 1-5
    6. Save screenshot of worst frame per event type
    7. Persist via stored procedures
    """
    start_time = time.time()
    logger.info(f"[AI] Starting disaster analysis {analysis_id}")

    db.execute(
        text("UPDATE analyses SET status='processing' WHERE id=:id"),
        {"id": analysis_id}
    )
    db.commit()

    try:
        model = YOLO(settings.YOLO_MODEL)
        model.fuse()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_interval = max(1, int(fps / FRAMES_PER_SECOND))

        logger.info(f"[AI] Disaster scan: sampling every {frame_interval} frames")

        # Accumulate events across frames: type → list of per-frame data
        event_accumulator: dict[str, list[dict]] = {}
        # Best frame (highest confidence) per disaster type for screenshot
        best_frames: dict[str, tuple[np.ndarray, float, int, float]] = {}  # type → (frame, conf, frame_idx, timestamp)

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp_sec = frame_idx / fps
                results = model(frame, verbose=False, conf=settings.CONFIDENCE_THRESHOLD)

                for result in results:
                    if result.boxes is None or len(result.boxes) == 0:
                        continue

                    frame_events = _classify_frame_disaster(frame, result.boxes, model.names)

                    for event in frame_events:
                        dtype = event["type"]
                        if dtype not in event_accumulator:
                            event_accumulator[dtype] = []
                        event_accumulator[dtype].append({
                            **event,
                            "frame_idx": frame_idx,
                            "timestamp": timestamp_sec,
                        })

                        # Track best frame for screenshot
                        if dtype not in best_frames or event["confidence"] > best_frames[dtype][1]:
                            best_frames[dtype] = (frame.copy(), event["confidence"], frame_idx, timestamp_sec)

            frame_idx += 1

        cap.release()

        # ── Persist confirmed events (seen in ≥2 frames = real, not noise) ──
        total_events = 0
        for dtype, occurrences in event_accumulator.items():
            if len(occurrences) < 2:
                # Single-frame detection — likely noise, skip
                continue

            avg_confidence = sum(o["confidence"] for o in occurrences) / len(occurrences)
            avg_area = sum(o["area_ratio"] for o in occurrences) / len(occurrences)
            total_count = sum(o["count"] for o in occurrences)
            best_timestamp = occurrences[0]["timestamp"]

            severity = _compute_severity(dtype, total_count, avg_confidence, avg_area)

            # Save screenshot of best frame
            screenshot_path = None
            if dtype in best_frames:
                best_frame, _, _, _ = best_frames[dtype]
                screenshot_path = _save_screenshot(best_frame, f"disaster_{analysis_id}_{dtype}")

            recommendation = DISASTER_RECOMMENDATIONS.get(dtype, "Assess situation and deploy appropriate response teams.")

            db.execute(
                text("""
                    SELECT record_disaster_event(
                        :analysis_id, :disaster_type, :severity, :confidence,
                        :affected_area, NULL, NULL, :timestamp, :frame_number,
                        :recommendations
                    )
                """),
                {
                    "analysis_id": analysis_id,
                    "disaster_type": dtype,
                    "severity": severity,
                    "confidence": avg_confidence,
                    "affected_area": avg_area * 10000,  # rough sq meter estimate
                    "timestamp": best_timestamp,
                    "frame_number": best_frames.get(dtype, (None, None, 0, None))[2],
                    "recommendations": recommendation,
                }
            )

            # Update screenshot path separately
            if screenshot_path:
                db.execute(
                    text("""
                        UPDATE disaster_events SET screenshot_path=:path
                        WHERE analysis_id=:aid AND disaster_type=:dtype
                        ORDER BY id DESC LIMIT 1
                    """),
                    {"path": screenshot_path, "aid": analysis_id, "dtype": dtype}
                )

            total_events += 1
            logger.info(f"[AI] Disaster event: {dtype} | severity={severity} | conf={avg_confidence:.2f}")

        db.commit()

        processing_time = time.time() - start_time
        db.execute(
            text("SELECT complete_analysis(:id, :total, :time)"),
            {"id": analysis_id, "total": total_events, "time": processing_time}
        )
        db.commit()

        logger.info(f"[AI] Disaster analysis {analysis_id} complete: {total_events} events in {processing_time:.1f}s")
        return {
            "analysis_id": analysis_id,
            "total_events": total_events,
            "processing_time": processing_time,
        }

    except Exception as e:
        logger.error(f"[AI] Disaster analysis {analysis_id} FAILED: {e}")
        db.execute(
            text("UPDATE analyses SET status='failed' WHERE id=:id"),
            {"id": analysis_id}
        )
        db.commit()
        raise
