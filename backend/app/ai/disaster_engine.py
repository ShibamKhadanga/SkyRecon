"""
SkyRecon – Disaster Detection Engine
Classifies disaster events, assigns severity 1-5, captures screenshots.
Fixed: PostgreSQL UPDATE bug, real progress tracking, image support.
"""

import cv2
import os
import time
import logging

import numpy as np
from ultralytics import YOLO
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.config import settings
from .video_processor import _save_screenshot, _draw_and_save, FRAMES_PER_SECOND, _write_progress, _get_model

logger = logging.getLogger(__name__)

DISASTER_TRIGGERS: dict[str, list[str]] = {
    "fire":       ["fire", "flame"],
    "flood":      ["boat", "water"],
    "structural": ["building", "house"],
    "people":     ["person"],
    "vehicles":   ["car", "truck", "bus"],
    "trees":      ["tree"],
    "poles":      ["pole"],
}

DISASTER_RELEVANT_CLASSES = {
    "person", "car", "truck", "bus", "motorcycle",
    "boat", "fire hydrant", "stop sign",
}

SEVERITY_WEIGHTS = {
    "fire": 5, "flood": 4, "structural": 3,
    "people": 1, "vehicles": 1, "trees": 1, "poles": 1,
}

# Minimum frames a disaster type must appear in before it's confirmed.
# Prevents false positives from a single noisy frame.
MIN_OCCURRENCES = 3  # must appear in at least 3 sampled frames

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


def _compute_severity(disaster_type: str, detection_count: int,
                      avg_confidence: float, affected_area_ratio: float) -> int:
    base = SEVERITY_WEIGHTS.get(disaster_type, 2)
    density_bonus = min(2, detection_count // 3)
    area_bonus = 1 if affected_area_ratio > 0.30 else 0
    conf_factor = 1 if avg_confidence > 0.55 else 0
    severity = base + density_bonus + area_bonus - (1 - conf_factor)
    return max(1, min(5, int(severity)))


def _classify_frame_disaster(frame: np.ndarray, boxes, names: dict) -> list[dict]:
    h, w = frame.shape[:2]
    frame_area = h * w
    type_data: dict[str, dict] = {}

    for box in boxes:
        cls_id = int(box.cls[0])
        cls_name = names[cls_id].lower()
        confidence = float(box.conf[0])

        matched_type = None
        for dtype, triggers in DISASTER_TRIGGERS.items():
            if cls_name in triggers:
                matched_type = dtype
                break
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

    return [
        {
            "type": dtype,
            "confidence": sum(d["confidences"]) / len(d["confidences"]),
            "area_ratio": min(1.0, d["area_ratio"]),
            "count": d["count"],
        }
        for dtype, d in type_data.items()
    ]


def run_disaster_analysis(analysis_id: int, video_path: str, db: Session) -> dict:
    start_time = time.time()
    logger.info(f"[AI] Disaster analysis {analysis_id}")

    db.execute(text("UPDATE analyses SET status='processing' WHERE id=:id"), {"id": analysis_id})
    db.commit()

    try:
        model = _get_model(settings.YOLO_MODEL)

        is_image = video_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))

        if is_image:
            frame = cv2.imread(video_path)
            if frame is None:
                raise RuntimeError(f"Cannot read image: {video_path}")
            frames_iter = [(0, 0.0, frame)]
            total_frames = 1
        else:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise RuntimeError(f"Cannot open video: {video_path}")
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_interval = max(1, int(fps / FRAMES_PER_SECOND))
            frames_iter = None

        # Accumulate events: type → list of per-frame data
        event_accumulator: dict[str, list[dict]] = {}
        # Best frame per disaster type for screenshot
        best_frames: dict[str, tuple[np.ndarray, float, int, float]] = {}

        last_progress = 0

        if is_image:
            for frame_idx, timestamp_sec, frame in frames_iter:
                results = model(frame, verbose=False, conf=settings.CONFIDENCE_THRESHOLD)
                for result in results:
                    if result.boxes is None or len(result.boxes) == 0:
                        continue
                    for event in _classify_frame_disaster(frame, result.boxes, model.names):
                        dtype = event["type"]
                        event_accumulator.setdefault(dtype, []).append(
                            {**event, "frame_idx": frame_idx, "timestamp": timestamp_sec}
                        )
                        if dtype not in best_frames or event["confidence"] > best_frames[dtype][1]:
                            best_frames[dtype] = (frame.copy(), event["confidence"], frame_idx, timestamp_sec)
            _write_progress(db, analysis_id, 90, 0)
        else:
            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_interval == 0:
                    timestamp_sec = frame_idx / fps

                    # Resize before inference for CPU speed
                    h, w = frame.shape[:2]
                    if w > 640:
                        frame_small = cv2.resize(frame, (640, int(h * 640 / w)))
                    else:
                        frame_small = frame

                    results = model(frame_small, verbose=False, conf=settings.CONFIDENCE_THRESHOLD)

                    for result in results:
                        if result.boxes is None or len(result.boxes) == 0:
                            continue
                        for event in _classify_frame_disaster(frame, result.boxes, model.names):
                            dtype = event["type"]
                            event_accumulator.setdefault(dtype, []).append(
                                {**event, "frame_idx": frame_idx, "timestamp": timestamp_sec}
                            )
                            if dtype not in best_frames or event["confidence"] > best_frames[dtype][1]:
                                best_frames[dtype] = (frame.copy(), event["confidence"], frame_idx, timestamp_sec)

                    # Write real progress
                    if total_frames > 0:
                        pct = min(90, int((frame_idx / total_frames) * 100))
                        if pct >= last_progress + 5:
                            _write_progress(db, analysis_id, pct, 0)
                            last_progress = pct
                            logger.info(f"[AI] Disaster progress: {pct}%")

                frame_idx += 1
            cap.release()

        # ── Persist confirmed events ──
        # Require MIN_OCCURRENCES frames to confirm a real disaster event
        min_occurrences = 1 if is_image else MIN_OCCURRENCES
        total_events = 0

        for dtype, occurrences in event_accumulator.items():
            if len(occurrences) < min_occurrences:
                continue

            avg_confidence = sum(o["confidence"] for o in occurrences) / len(occurrences)
            avg_area = sum(o["area_ratio"] for o in occurrences) / len(occurrences)
            total_count = sum(o["count"] for o in occurrences)
            best_timestamp = occurrences[0]["timestamp"]
            severity = _compute_severity(dtype, total_count, avg_confidence, avg_area)

            # Save screenshot with timestamp burned in
            screenshot_path = None
            if dtype in best_frames:
                bf, _, bf_idx, bf_ts = best_frames[dtype]
                screenshot_path = _draw_and_save(
                    bf, None, model.names,
                    f"disaster_{analysis_id}_{dtype}", bf_ts
                ) if False else _save_screenshot(bf, f"disaster_{analysis_id}_{dtype}", bf_ts)

            recommendation = DISASTER_RECOMMENDATIONS.get(
                dtype, "Assess situation and deploy appropriate response teams."
            )

            # Insert disaster event
            result = db.execute(
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
                    "affected_area": avg_area * 10000,
                    "timestamp": best_timestamp,
                    "frame_number": best_frames.get(dtype, (None, None, 0, None))[2],
                    "recommendations": recommendation,
                }
            )
            new_event_id = result.scalar()

            # ── FIX: Use the returned ID directly — no ORDER BY/LIMIT needed ──
            if screenshot_path and new_event_id:
                db.execute(
                    text("UPDATE disaster_events SET screenshot_path=:path WHERE id=:id"),
                    {"path": screenshot_path, "id": new_event_id}
                )

            total_events += 1
            logger.info(f"[AI] Event: {dtype} | sev={severity} | conf={avg_confidence:.2f}")

        db.commit()

        processing_time = time.time() - start_time
        db.execute(
            text("SELECT complete_analysis(:id, :total, :time)"),
            {"id": analysis_id, "total": total_events, "time": processing_time}
        )
        db.commit()

        logger.info(f"[AI] Disaster done: {total_events} events in {processing_time:.1f}s")
        return {"analysis_id": analysis_id, "total_events": total_events,
                "processing_time": processing_time}

    except Exception as e:
        logger.error(f"[AI] Disaster FAILED {analysis_id}: {e}", exc_info=True)
        db.execute(text("UPDATE analyses SET status='failed' WHERE id=:id"), {"id": analysis_id})
        db.commit()
        raise
