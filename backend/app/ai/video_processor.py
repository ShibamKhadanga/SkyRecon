"""
SkyRecon – Core AI Video Processing Engine
Uses YOLOv8 + ByteTrack for YOLO-detectable categories.
Uses OpenCV heuristics + ExG vegetation index for aerial-specific categories.
Uses SegFormer-B2 (HuggingFace) for pixel-level segmentation of trees, water, buildings.

Domain gap fix:
  YOLOv8 COCO was trained on ground-level photos — not aerial drone footage.
  For categories where COCO has no matching class (trees, rooftops, water bodies etc.)
  we use purpose-built aerial detectors instead of forcing wrong COCO classes.
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

# ── SegFormer segmentation model cache ───────────────────────────────────────
_seg_model_cache: dict = {}
_seg_frame_counter: dict = {}  # category -> frame count, for subsampling
SEG_SUBSAMPLE = 5  # run SegFormer every Nth heuristic frame

def _get_seg_model():
    """
    Load SegFormer-B2 fine-tuned on ADE20K (includes vegetation, building, water classes).
    Falls back gracefully if transformers not installed.
    Cached after first load.
    """
    if "segformer" in _seg_model_cache:
        return _seg_model_cache["segformer"]
    try:
        from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
        import torch
        processor = SegformerImageProcessor.from_pretrained("nvidia/segformer-b2-finetuned-ade-512-512")
        model = SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b2-finetuned-ade-512-512")
        model.eval()
        _seg_model_cache["segformer"] = (processor, model)
        logger.info("[AI] SegFormer-B2 loaded for aerial segmentation")
        return _seg_model_cache["segformer"]
    except Exception as e:
        logger.warning(f"[AI] SegFormer not available ({e}), falling back to OpenCV heuristics")
        _seg_model_cache["segformer"] = None
        return None


# ADE20K class IDs relevant to SkyRecon aerial categories
# Full list: https://huggingface.co/nvidia/segformer-b2-finetuned-ade-512-512
ADE20K_CLASSES = {
    4:  "tree",          # tree
    9:  "grass",         # grass (used to separate from trees)
    21: "water",         # water, lake
    26: "sea",           # sea/ocean
    29: "building",      # building, skyscraper
    48: "house",         # house
    52: "road",          # road, route
    53: "fence",         # fence
    60: "field",         # field (agricultural)
    72: "river",         # river
    80: "bridge",        # bridge
    96: "plant",         # plant, flora
}
SEG_CATEGORY_MAP = {
    "trees":             {4, 96},
    "plants":            {96, 9},
    "water bodies":      {21, 26, 72},
    "flood water":       {21, 26, 72},
    "buildings":         {29},
    "houses":            {48, 29},
    "roads":             {52},
    "agricultural land": {60, 9},
    "bridges":           {80},
}


def _run_segformer(
    frame: np.ndarray,
    target_cat: str,
    force: bool = False,
) -> Optional[np.ndarray]:
    """
    Run SegFormer-B2 on a frame and return a binary mask for the target category.
    Subsampled to every SEG_SUBSAMPLE calls. Returns None if unavailable or skipped.
    """
    global _seg_frame_counter
    key = target_cat.strip().lower()
    _seg_frame_counter[key] = _seg_frame_counter.get(key, 0) + 1
    if not force and _seg_frame_counter[key] % SEG_SUBSAMPLE != 1:
        return None
    seg = _get_seg_model()
    if seg is None:
        return None
    try:
        import torch
        from PIL import Image as PILImage
        processor, model = seg
        h, w = frame.shape[:2]
        pil_img = PILImage.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        inputs = processor(images=pil_img, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        logits = outputs.logits  # (1, num_classes, H/4, W/4)
        upsampled = torch.nn.functional.interpolate(
            logits, size=(h, w), mode="bilinear", align_corners=False
        )
        pred = upsampled.argmax(dim=1).squeeze().numpy().astype(np.uint8)
        target_ids = SEG_CATEGORY_MAP.get(target_cat.strip().lower(), set())
        if not target_ids:
            return None
        mask = np.zeros((h, w), dtype=np.uint8)
        for cls_id in target_ids:
            mask[pred == cls_id] = 255
        return mask
    except Exception as e:
        logger.debug(f"[AI] SegFormer inference failed: {e}")
        return None

# ── PyTorch thread configuration — must run BEFORE any model is loaded ─────────
# torch.set_num_interop_threads() cannot be called after parallel work starts,
# so we configure it once at module-import time.
try:
    import torch as _torch
    _cpu_count = os.cpu_count() or 4
    _intra = max(1, _cpu_count // 2)
    _inter = max(1, _cpu_count - _intra)
    try:
        _torch.set_num_threads(_intra)
    except RuntimeError:
        pass  # already set
    try:
        _torch.set_num_interop_threads(_inter)
    except RuntimeError:
        pass  # already set or parallel work already started
    logger.info(f"[AI] PyTorch threads configured: intra={_intra}, inter={_inter}")
except ImportError:
    pass  # torch not installed yet

# ── Model cache — load once per process, reuse across all analyses ────────────
_model_cache: dict[str, YOLO] = {}

# ── Specialist model registry ─────────────────────────────────────────────────
# Fine-tuned models override the base model for specific categories.
# Falls back to base YOLO model if specialist file is not present.
SPECIALIST_MODELS: dict[str, str] = {
    "people":             "skyrecon_visdrone.pt",
    "vehicles":           "skyrecon_visdrone.pt",
    "road potholes":      "skyrecon_rdd2022.pt",
    "fire & smoke":       "skyrecon_fire_smoke.pt",
    "flood water":        "skyrecon_flood.pt",
    "trees":              "skyrecon_trees_plants.pt",
    "plants":             "skyrecon_trees_plants.pt",
    "buildings":          "skyrecon_buildings.pt",
    "houses":             "skyrecon_buildings.pt",
    "warehouses":         "skyrecon_buildings.pt",
    "shops":              "skyrecon_buildings.pt",
    "solar panels":       "skyrecon_solar_panels.pt",
}

def _get_model(model_path: str) -> YOLO:
    """Load and cache YOLO model."""
    if model_path not in _model_cache:
        logger.info(f"[AI] Loading model: {model_path}")
        m = YOLO(model_path)
        m.fuse()
        _model_cache[model_path] = m
        logger.info(f"[AI] Model ready.")
    return _model_cache[model_path]


def _get_model_for_category(base_model_path: str, category: str) -> YOLO:
    """
    Returns the best available model for a given category.
    Uses specialist fine-tuned model if present, otherwise falls back to base.
    """
    cat_lower = category.strip().lower()
    specialist = SPECIALIST_MODELS.get(cat_lower)
    if specialist and os.path.exists(specialist):
        logger.info(f"[AI] Using specialist model '{specialist}' for category '{category}'")
        return _get_model(specialist)
    return _get_model(base_model_path)


# ── YOLO COCO class → SkyRecon category ──────────────────────────────────────
YOLO_TO_CATEGORY: dict[str, str] = {
    "car": "Vehicles", "truck": "Vehicles", "bus": "Vehicles",
    "motorcycle": "Vehicles", "bicycle": "Vehicles",
    "boat": "Water Bodies", "train": "Railway Tracks", "airplane": "Vehicles",
    "person": "People",
    "cat": "Animals", "dog": "Animals", "horse": "Animals",
    "cow": "Animals", "sheep": "Animals", "bird": "Animals",
    "elephant": "Animals", "bear": "Animals", "zebra": "Animals",
    "giraffe": "Animals",
    "traffic light": "Traffic Lights",
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
    "solar-panel": "Solar Panels",
    "Building":    "Buildings",
}

# ── Heuristic-only categories (not detectable via YOLO COCO classes) ──────────
# These use OpenCV image analysis instead of / in addition to YOLO.
HEURISTIC_CATEGORIES = {
    "trees", "plants", "road potholes", "water bodies", "flood water",
    "fire & smoke", "solar panels", "agricultural land",
    "construction zones", "parking areas", "roads",
    "electric poles", "street lights", "buildings", "houses",
    "bridges", "warehouses", "shops", "pipelines",
}


def _region_hsv_ratio(frame: np.ndarray, lower: list[int], upper: list[int]) -> float:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
    return cv2.countNonZero(mask) / max(1, frame.shape[0] * frame.shape[1])


def _vertical_edge_density(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    vertical = np.abs(sobelx)
    return np.count_nonzero(vertical > 40) / max(1, vertical.size)


def _infer_color_label(frame: np.ndarray) -> str:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mean_h = float(np.mean(hsv[:, :, 0]))
    mean_s = float(np.mean(hsv[:, :, 1]))
    mean_v = float(np.mean(hsv[:, :, 2]))
    if mean_v < 50:
        return "Black"
    if mean_s < 40 and mean_v > 180:
        return "White"
    if mean_s < 45 and 80 < mean_v < 220:
        return "Grey"
    if mean_h <= 10 or mean_h >= 160:
        return "Red"
    if 20 <= mean_h <= 35:
        return "Yellow"
    if 35 < mean_h <= 85:
        return "Green"
    if 85 < mean_h <= 140:
        return "Blue"
    return "Silver"


def _matches_characteristics(
    target_cat: str,
    characteristics: dict,
    cls_name: str | None,
    crop: np.ndarray | None,
) -> bool:
    if not characteristics or not isinstance(characteristics, dict):
        return True
    cat_lower = target_cat.strip().lower()

    if cat_lower == "vehicles":
        vehicle_type = characteristics.get("type", "All")
        if vehicle_type != "All" and cls_name is not None:
            vehicle_filters = {
                "Light Vehicle (Sedan/SUV)": {"car"},
                "Heavy Vehicle (Truck/Bus)": {"truck", "bus"},
                "2-Wheeler": {"motorcycle", "bicycle"},
                "3-Wheeler": {"motorcycle", "bicycle"},
                "4-Wheeler": {"car", "truck", "bus"},
                "Bike": {"bicycle", "motorcycle"},
                "Scooty": {"motorcycle", "bicycle"},
                "Car": {"car"},
                "Bus": {"bus"},
                "Truck": {"truck"},
            }
            allowed = vehicle_filters.get(vehicle_type, {cls_name})
            if cls_name not in allowed:
                return False
        vehicle_color = characteristics.get("color", "All")
        if vehicle_color != "All" and crop is not None:
            detected_color = _infer_color_label(crop)
            if detected_color != vehicle_color:
                return False

    if cat_lower == "trees":
        tree_health = characteristics.get("health", "All")
        if tree_health != "All" and crop is not None:
            green_ratio = _region_hsv_ratio(crop, [25, 40, 40], [95, 255, 255])
            if tree_health == "Healthy Green" and green_ratio < 0.5:
                return False
            if tree_health == "Diseased/Dry" and green_ratio > 0.45:
                return False
        tree_type = characteristics.get("type", "All")
        if tree_type == "Large trees" and crop is not None:
            if crop.shape[0] * crop.shape[1] < 16000:
                return False
        if tree_type == "Dry trees" and crop is not None:
            green_ratio = _region_hsv_ratio(crop, [25, 40, 40], [95, 255, 255])
            if green_ratio > 0.45:
                return False

    if cat_lower == "buildings" and characteristics.get("type") != "All":
        # No reliable building-type inference from default YOLO; keep broad coverage.
        pass

    return True


def _detect_heuristic(
    frame: np.ndarray,
    target_cat: str,
    frame_idx: int,
    timestamp_sec: float,
    analysis_id: int,
    cat_id: int,
    chars_str: str,
    seen_track_ids: dict,
    obj_screenshots: dict,
    batch: list,
    settings_ref,
):
    """
    OpenCV-based heuristic detectors for categories not covered by YOLO COCO.
    Each detector returns a list of bounding boxes (x1,y1,x2,y2,label,conf).
    """
    h, w = frame.shape[:2]
    cat_lower = target_cat.strip().lower()
    detections = []  # list of (x1,y1,x2,y2,label,conf)

    # ── Trees: SegFormer (primary) + ExG vegetation index (fallback) ─────────
    if cat_lower == "trees":
        seg_mask = _run_segformer(frame, target_cat)
        if seg_mask is not None:
            # SegFormer path — pixel-level tree canopy mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (18, 18))
            seg_mask = cv2.morphologyEx(seg_mask, cv2.MORPH_CLOSE, kernel)
            seg_mask = cv2.morphologyEx(seg_mask, cv2.MORPH_OPEN,
                                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10)))
            contours, _ = cv2.findContours(seg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        else:
            # Fallback: ExG (Excess Green Index) + HSV green masking
            # ExG = 2*G - R - B  (works on standard RGB drone footage, no ML needed)
            b_ch = frame[:, :, 0].astype(np.float32)
            g_ch = frame[:, :, 1].astype(np.float32)
            r_ch = frame[:, :, 2].astype(np.float32)
            exg = 2.0 * g_ch - r_ch - b_ch
            # Normalize to 0-255
            exg_norm = cv2.normalize(exg, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            # Threshold: pixels with ExG > 0.12 * 255 are vegetation
            _, exg_mask = cv2.threshold(exg_norm, 30, 255, cv2.THRESH_BINARY)
            # Also use HSV green range as secondary confirmation
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hsv_mask = cv2.inRange(hsv, np.array([22, 25, 20]), np.array([95, 255, 255]))
            # Combine: pixel must pass EITHER ExG OR HSV green
            combined = cv2.bitwise_or(exg_mask, hsv_mask)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
            combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
            combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN,
                                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
            contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = (w * h) * 0.0008
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            if aspect > 5.0 or aspect < 0.18:
                continue
            crop = frame[y:y+bh, x:x+bw]
            if crop.size == 0:
                continue
            # Reject sky-dominated regions
            sky_ratio = _region_hsv_ratio(crop, [90, 15, 100], [140, 255, 255])
            if sky_ratio > 0.40:
                continue
            # Solidity check: trees have irregular canopy edges (solidity < 0.92)
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = area / max(hull_area, 1)
            if solidity > 0.97:  # too regular — likely a building rooftop
                continue
            conf = min(0.93, 0.58 + (area / (w * h)) * 2.5)
            if not _matches_characteristics(target_cat, json.loads(chars_str or '{}'), None, crop):
                continue
            detections.append((x, y, x + bw, y + bh, "tree", conf))

    # ── Plants: SegFormer + ExG green index (smaller vegetation) ─────────────
    elif cat_lower == "plants":
        seg_mask = _run_segformer(frame, target_cat)
        if seg_mask is not None:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (12, 12))
            seg_mask = cv2.morphologyEx(seg_mask, cv2.MORPH_CLOSE, kernel)
            seg_mask = cv2.morphologyEx(seg_mask, cv2.MORPH_OPEN,
                                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (6, 6)))
            contours, _ = cv2.findContours(seg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        else:
            # Fallback: ExG vegetation index + broader HSV green for smaller plants
            b_ch = frame[:, :, 0].astype(np.float32)
            g_ch = frame[:, :, 1].astype(np.float32)
            r_ch = frame[:, :, 2].astype(np.float32)
            exg = 2.0 * g_ch - r_ch - b_ch
            exg_norm = cv2.normalize(exg, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            _, exg_mask = cv2.threshold(exg_norm, 25, 255, cv2.THRESH_BINARY)
            # Broader HSV green range to catch lighter / potted plants
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hsv_mask = cv2.inRange(hsv, np.array([20, 20, 15]), np.array([100, 255, 255]))
            combined = cv2.bitwise_or(exg_mask, hsv_mask)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (10, 10))
            combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)
            combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN,
                                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
            contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Lower min area than trees — plants/shrubs can be much smaller
        min_area = (w * h) * 0.0003
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            if aspect > 6.0 or aspect < 0.15:
                continue
            crop = frame[y:y+bh, x:x+bw]
            if crop.size == 0:
                continue
            # Reject sky-dominated regions
            sky_ratio = _region_hsv_ratio(crop, [90, 15, 100], [140, 255, 255])
            if sky_ratio > 0.40:
                continue
            conf = min(0.91, 0.55 + (area / (w * h)) * 3.0)
            if not _matches_characteristics(target_cat, json.loads(chars_str or '{}'), None, crop):
                continue
            detections.append((x, y, x + bw, y + bh, "plant", conf))

    # ── Road Potholes: dark circular blobs on road surface ───────────────────
    elif cat_lower == "road potholes":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)
        # Potholes are darker than surrounding road
        _, dark_mask = cv2.threshold(blurred, 0, 255,
                                     cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * 0.001
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            if aspect > 5.0 or aspect < 0.2:
                continue
            conf = min(0.88, 0.50 + (area / (w * h)) * 4.0)
            detections.append((x, y, x + bw, y + bh, "pothole", conf))

    # ── Water Bodies / Flood Water: SegFormer (primary) + HSV (fallback) ──────
    elif cat_lower in ("water bodies", "flood water"):
        seg_mask = _run_segformer(frame, cat_lower)
        if seg_mask is not None:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
            seg_mask = cv2.morphologyEx(seg_mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(seg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        else:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            mask1 = cv2.inRange(hsv, np.array([90, 30, 30]),  np.array([140, 255, 255]))
            mask2 = cv2.inRange(hsv, np.array([10, 10, 60]),  np.array([30, 80, 180]))
            mask = cv2.bitwise_or(mask1, mask2)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 20))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                    cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10)))
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * 0.005
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            conf = min(0.92, 0.55 + (area / (w * h)) * 2.0)
            label = "flood water" if cat_lower == "flood water" else "water body"
            detections.append((x, y, x + bw, y + bh, label, conf))

    # ── Fire & Smoke: orange/red/white HSV range ──────────────────────────────
    elif cat_lower == "fire & smoke":
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Fire: orange-red
        fire_mask = cv2.inRange(hsv, np.array([0, 100, 150]),  np.array([25, 255, 255]))
        # Smoke: low saturation, medium-high value (grey/white)
        smoke_mask = cv2.inRange(hsv, np.array([0, 0, 160]),   np.array([180, 40, 255]))
        for mask, label in [(fire_mask, "fire"), (smoke_mask, "smoke")]:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (12, 12))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            min_area = (w * h) * 0.002
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < min_area:
                    continue
                x, y, bw, bh = cv2.boundingRect(cnt)
                conf = min(0.93, 0.60 + (area / (w * h)) * 3.0)
                detections.append((x, y, x + bw, y + bh, label, conf))

    # ── Solar Panels: dark blue rectangular regions on rooftops ──────────────
    elif cat_lower == "solar panels":
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([100, 40, 20]), np.array([140, 255, 120]))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * 0.002
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            if aspect > 6.0 or aspect < 0.15:
                continue
            conf = min(0.85, 0.50 + (area / (w * h)) * 3.0)
            detections.append((x, y, x + bw, y + bh, "solar panel", conf))

    # ── Agricultural Land: large uniform green/brown patches ─────────────────
    elif cat_lower == "agricultural land":
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Crop green
        green = cv2.inRange(hsv, np.array([30, 40, 40]),  np.array([90, 255, 200]))
        # Bare/harvested brown soil
        brown = cv2.inRange(hsv, np.array([8, 30, 40]),   np.array([25, 180, 180]))
        mask = cv2.bitwise_or(green, brown)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 30))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * 0.02  # agricultural plots are large
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            conf = min(0.88, 0.55 + (area / (w * h)) * 1.5)
            detections.append((x, y, x + bw, y + bh, "agricultural plot", conf))

    # ── Roads: grey/asphalt linear regions ───────────────────────────────────
    elif cat_lower == "roads":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Asphalt: low saturation, mid-dark value
        road_mask = cv2.inRange(hsv, np.array([0, 0, 40]), np.array([180, 40, 160]))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
        road_mask = cv2.morphologyEx(road_mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(road_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * 0.01
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            # Roads are elongated
            if aspect < 1.5 and bh / max(bw, 1) < 1.5:
                continue
            conf = min(0.85, 0.50 + (area / (w * h)) * 1.5)
            detections.append((x, y, x + bw, y + bh, "road", conf))

    # ── Electric Poles / Street Lights: tall narrow vertical objects ──────────
    elif cat_lower in ("electric poles", "street lights"):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
        dilated = cv2.dilate(edges, kernel_v, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * 0.00025
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bh / max(bw, 1)  # height/width
            if aspect < 4.0 or bw > w * 0.12:
                continue
            crop = frame[y:y+bh, x:x+bw]
            if crop.size == 0:
                continue
            sky_ratio = _region_hsv_ratio(crop, [90, 15, 100], [140, 255, 255])
            if sky_ratio > 0.38:
                continue
            vertical_density = _vertical_edge_density(crop)
            if vertical_density < 0.018:
                continue
            material_ratio = _region_hsv_ratio(crop, [0, 0, 0], [180, 90, 200])
            if material_ratio < 0.10:
                continue
            conf = min(0.88, 0.55 + min(vertical_density, 0.08) * 2.0)
            label = "street light" if cat_lower == "street lights" else "electric pole"
            detections.append((x, y, x + bw, y + bh, label, conf))

    # ── Buildings / Houses / Warehouses / Shops: SegFormer + geometric solidity ──
    elif cat_lower in ("buildings", "houses", "warehouses", "shops"):
        seg_mask = _run_segformer(frame, cat_lower)
        if seg_mask is not None:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
            seg_mask = cv2.morphologyEx(seg_mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(seg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 30, 100)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (8, 8))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * (0.0025 if cat_lower == "houses" else 0.005)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
            if len(approx) < 4:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = bw / max(bh, 1)
            if aspect > 7.5 or aspect < 0.15:
                continue
            crop = frame[y:y+bh, x:x+bw]
            if crop.size == 0:
                continue
            # ── Geometric solidity filter ──────────────────────────────────────────
            # Buildings have straight edges → solidity > 0.82 (rectangular)
            # Trees have irregular canopy edges → solidity < 0.70
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = area / max(hull_area, 1)
            if solidity < 0.55:  # too irregular — likely a tree canopy
                continue
            # ── Color signal: rooftops have characteristic colors ────────────────
            roof_red    = _region_hsv_ratio(crop, [0, 80, 80],   [12, 255, 255])
            roof_orange = _region_hsv_ratio(crop, [10, 80, 80],  [25, 255, 255])
            roof_brown  = _region_hsv_ratio(crop, [8, 30, 40],   [28, 200, 220])
            roof_gray   = _region_hsv_ratio(crop, [0, 0, 60],    [180, 50, 220])
            roof_white  = _region_hsv_ratio(crop, [0, 0, 180],   [180, 50, 255])
            green_ratio = _region_hsv_ratio(crop, [25, 40, 40],  [95, 255, 255])
            blue_ratio  = _region_hsv_ratio(crop, [90, 15, 70],  [140, 255, 255])
            color_signal = roof_red + roof_orange + roof_brown + roof_gray + roof_white
            # Reject if dominated by vegetation or sky
            if green_ratio > 0.60 and color_signal < 0.12:
                continue
            if blue_ratio > 0.70 and color_signal < 0.12:
                continue
            conf = min(0.88, 0.50 + solidity * 0.25 + min(color_signal, 0.20))
            detections.append((x, y, x + bw, y + bh, cat_lower.rstrip('s'), conf))

    # ── Parking Areas: large flat rectangular regions with vehicles ───────────
    elif cat_lower == "parking areas":
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Concrete/asphalt parking lots: low saturation, medium value
        mask = cv2.inRange(hsv, np.array([0, 0, 80]), np.array([180, 35, 200]))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * 0.02
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            conf = min(0.82, 0.50 + (area / (w * h)) * 1.5)
            detections.append((x, y, x + bw, y + bh, "parking area", conf))

    # ── Construction Zones: exposed earth/sand + machinery colors ────────────
    elif cat_lower == "construction zones":
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Exposed earth: orange-brown
        earth = cv2.inRange(hsv, np.array([8, 40, 60]),  np.array([28, 200, 220]))
        # Yellow machinery / construction materials
        yellow = cv2.inRange(hsv, np.array([18, 100, 100]), np.array([35, 255, 255]))
        mask = cv2.bitwise_or(earth, yellow)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * 0.004
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            crop = frame[y:y+bh, x:x+bw]
            if crop.size == 0:
                continue
            earth_ratio = _region_hsv_ratio(crop, [8, 40, 60], [28, 200, 220])
            yellow_ratio = _region_hsv_ratio(crop, [18, 100, 100], [35, 255, 255])
            green_ratio = _region_hsv_ratio(crop, [35, 40, 40], [95, 255, 255])
            if earth_ratio + yellow_ratio < 0.12:
                continue
            if green_ratio > 0.25:
                continue
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 40, 120)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            if edge_density < 0.015 and yellow_ratio < 0.06:
                continue
            if area / max(1, bw * bh) < 0.55:
                continue
            conf = min(0.88, 0.52 + (earth_ratio + yellow_ratio) * 1.8)
            detections.append((x, y, x + bw, y + bh, "construction zone", conf))

    # ── Bridges / Pipelines: elongated linear structures ─────────────────────
    elif cat_lower in ("bridges", "pipelines"):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 40, 120)
        # Horizontal kernel for bridges, both for pipelines
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 3))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 30))
        h_lines = cv2.dilate(edges, kernel_h, iterations=2)
        v_lines = cv2.dilate(edges, kernel_v, iterations=2)
        mask = cv2.bitwise_or(h_lines, v_lines)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (w * h) * 0.003
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = max(bw, bh) / max(min(bw, bh), 1)
            if aspect < 3.0:  # must be elongated
                continue
            conf = min(0.82, 0.50 + (area / (w * h)) * 2.0)
            detections.append((x, y, x + bw, y + bh, cat_lower.rstrip('s'), conf))

    # ── Now process all heuristic detections into batch ───────────────────────
    for (x1, y1, x2, y2, label, conf) in detections:
        # 75% confidence gate — only record high-confidence detections
        if conf < settings.MIN_DISPLAY_CONFIDENCE:
            continue
        # Centre-point spatial key on 25px grid
        spatial_key = (
            round((x1 + x2) / 2 / 25),
            round((y1 + y2) / 2 / 25),
            label
        )
        if spatial_key in seen_track_ids:
            continue
        seen_track_ids[spatial_key] = timestamp_sec

        # Save screenshot
        try:
            pad = 10
            cx1 = max(0, x1 - pad); cy1 = max(0, y1 - pad)
            cx2 = min(w, x2 + pad); cy2 = min(h, y2 + pad)
            crop = frame[cy1:cy2, cx1:cx2].copy()
            cv2.rectangle(crop, (x1 - cx1, y1 - cy1), (x2 - cx1, y2 - cy1), (57, 255, 20), 2)
            cv2.putText(crop, f"{label} {conf:.0%}",
                        (x1 - cx1, max(y1 - cy1 - 6, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (57, 255, 20), 2)
            shot_path = _save_screenshot(crop, f"map_{analysis_id}", timestamp_sec)
            obj_screenshots[spatial_key] = shot_path
        except Exception:
            shot_path = None

        batch.append({
            "analysis_id": analysis_id,
            "category_id": cat_id,
            "label": f"{label} ({conf:.0%}) first seen T={timestamp_sec:.1f}s",
            "confidence": conf,
            "bbox_x": x1 / w, "bbox_y": y1 / h,
            "bbox_w": (x2 - x1) / w, "bbox_h": (y2 - y1) / h,
            "frame_number": frame_idx,
            "timestamp": timestamp_sec,
            "characteristics": chars_str,
            "screenshot_path": obj_screenshots.get(spatial_key),
        })

# ── Aerial misclassification correction ───────────────────────────────────────
# From drone altitude, people are often misclassified as these COCO classes.
# We remap them back to People when the bbox shape matches a person.
# An actual kite is wide (aspect ratio > 1.5), a person is tall or square.
AERIAL_PERSON_MISCLASSES = {"kite", "frisbee", "sports ball", "surfboard", "skateboard"}

def _correct_aerial_misclassification(
    cls_name: str,
    x1: float, y1: float, x2: float, y2: float,
    target_cat: str,
) -> str:
    """
    Corrects common aerial-view misclassifications.
    A person seen from above/behind is often detected as kite, frisbee, etc.
    We check the bounding box shape:
      - Person shape: roughly square or taller than wide (aspect ratio <= 1.8)
      - Actual kite:  wide horizontal shape (aspect ratio > 1.8)
    Only applies when target category is People.
    """
    if cls_name not in AERIAL_PERSON_MISCLASSES:
        return cls_name
    if target_cat.lower() != "people":
        return cls_name  # only remap when looking for people

    w = x2 - x1
    h = y2 - y1
    if w <= 0:
        return cls_name

    aspect = w / h  # width/height ratio
    # Person from above: aspect ratio typically 0.3 – 1.8
    # Real kite/frisbee: aspect ratio typically > 1.8 or very small area
    if aspect <= 1.8:
        logger.debug(f"[AI] Remapped '{cls_name}' → 'person' (aspect={aspect:.2f})")
        return "person"
    return cls_name

# ── Per-category inference config ─────────────────────────────────────────────
# People from aerial view need tuned confidence to balance recall vs false positives
CATEGORY_SETTINGS: dict[str, dict] = {
    # Aerial people: conf=0.25 catches edge/partial people, CLIP dedup handles duplicates.
    # fps=4 catches fast walkers, iou=0.40 tighter NMS
    "people":             {"fps": 2, "conf": 0.25, "iou": 0.40},
    # Vehicles are large from above — higher conf reduces road-marking false positives
    "vehicles":           {"fps": 1, "conf": 0.42, "iou": 0.50},
    "animals":            {"fps": 2, "conf": 0.20, "iou": 0.40},
    # Fire/smoke: low conf to catch early-stage events
    "fire & smoke":       {"fps": 3, "conf": 0.25, "iou": 0.38},
    "flood water":        {"fps": 2, "conf": 0.28, "iou": 0.50},
    "water bodies":       {"fps": 1, "conf": 0.28, "iou": 0.50},
    "trees":              {"fps": 1, "conf": 0.28, "iou": 0.50},
    # Potted plants are small — low conf + higher fps to catch them from moving drone
    "plants":             {"fps": 2, "conf": 0.18, "iou": 0.45},
    "road potholes":      {"fps": 2, "conf": 0.28, "iou": 0.42},
    "roads":              {"fps": 1, "conf": 0.28, "iou": 0.50},
    "electric poles":     {"fps": 1, "conf": 0.28, "iou": 0.50},
    "street lights":      {"fps": 1, "conf": 0.28, "iou": 0.50},
    "buildings":          {"fps": 1, "conf": 0.30, "iou": 0.50},
    "houses":             {"fps": 1, "conf": 0.30, "iou": 0.50},
    "solar panels":       {"fps": 1, "conf": 0.28, "iou": 0.50},
    "agricultural land":  {"fps": 1, "conf": 0.28, "iou": 0.50},
    "construction zones": {"fps": 1, "conf": 0.28, "iou": 0.50},
    "parking areas":      {"fps": 1, "conf": 0.28, "iou": 0.50},
    "bridges":            {"fps": 1, "conf": 0.28, "iou": 0.50},
    "pipelines":          {"fps": 1, "conf": 0.28, "iou": 0.50},
    "warehouses":         {"fps": 1, "conf": 0.28, "iou": 0.50},
    "shops":              {"fps": 1, "conf": 0.28, "iou": 0.50},
    "default":            {"fps": 1, "conf": 0.35, "iou": 0.50},
}

FRAMES_PER_SECOND = 1   # fallback
MAX_SCREENSHOTS   = 8

# ── SAHI-style tiling for small object categories ─────────────────────────────
# These categories contain small objects that benefit from running YOLO on
# overlapping crops of the full-resolution frame instead of downscaling.
SAHI_CATEGORIES = {"people", "plants", "animals"}
# Inference resolution override for small-object categories (default is 640)
SMALL_OBJ_INFER_SIZE = 960


def _run_sahi_tiled(
    model: YOLO,
    frame: np.ndarray,
    conf: float,
    iou: float,
    overlap: float = 0.25,
) -> list:
    """
    SAHI-style Slicing Aided Hyper Inference.
    Splits the frame into 4 overlapping quadrants, runs YOLO on each at higher
    resolution, then merges all detections with NMS to remove duplicates.

    Returns a list of dicts: {x1, y1, x2, y2, cls_id, cls_name, conf, track_id}
    """
    h, w = frame.shape[:2]
    half_h = h // 2
    half_w = w // 2
    pad_h = int(half_h * overlap)
    pad_w = int(half_w * overlap)

    # Define 4 overlapping slices (y1, y2, x1, x2)
    slices = [
        (0,              half_h + pad_h, 0,              half_w + pad_w),  # top-left
        (0,              half_h + pad_h, half_w - pad_w, w),               # top-right
        (half_h - pad_h, h,              0,              half_w + pad_w),  # bottom-left
        (half_h - pad_h, h,              half_w - pad_w, w),               # bottom-right
    ]

    all_boxes = []   # (x1, y1, x2, y2) in original coords
    all_scores = []
    all_cls_ids = []
    all_cls_names = []

    for (sy1, sy2, sx1, sx2) in slices:
        crop = frame[sy1:sy2, sx1:sx2]
        if crop.size == 0:
            continue

        # Run YOLO on this crop (no tracking — tracking is done on merged results)
        try:
            results = model(
                crop, verbose=False, conf=conf, iou=iou,
                agnostic_nms=False, max_det=300,
            )
        except Exception:
            continue

        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue
            for box in result.boxes:
                bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                cls_id = int(box.cls[0])
                score = float(box.conf[0])
                # Map crop coords back to original frame coords
                all_boxes.append([
                    bx1 + sx1, by1 + sy1,
                    bx2 + sx1, by2 + sy1,
                ])
                all_scores.append(score)
                all_cls_ids.append(cls_id)
                all_cls_names.append(model.names[cls_id])

    if not all_boxes:
        return []

    # NMS to merge duplicate detections from overlapping tiles
    boxes_np = np.array(all_boxes, dtype=np.float32)
    scores_np = np.array(all_scores, dtype=np.float32)

    # Per-class NMS
    keep_indices = []
    unique_cls = set(all_cls_ids)
    for c in unique_cls:
        cls_mask = [i for i, cid in enumerate(all_cls_ids) if cid == c]
        if not cls_mask:
            continue
        cls_boxes = boxes_np[cls_mask]
        cls_scores = scores_np[cls_mask]

        # Simple greedy NMS
        order = cls_scores.argsort()[::-1]
        suppressed = set()
        for i_idx in range(len(order)):
            i = order[i_idx]
            if i in suppressed:
                continue
            keep_indices.append(cls_mask[i])
            for j_idx in range(i_idx + 1, len(order)):
                j = order[j_idx]
                if j in suppressed:
                    continue
                # Compute IoU
                ix1 = max(cls_boxes[i][0], cls_boxes[j][0])
                iy1 = max(cls_boxes[i][1], cls_boxes[j][1])
                ix2 = min(cls_boxes[i][2], cls_boxes[j][2])
                iy2 = min(cls_boxes[i][3], cls_boxes[j][3])
                inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                area_i = (cls_boxes[i][2] - cls_boxes[i][0]) * (cls_boxes[i][3] - cls_boxes[i][1])
                area_j = (cls_boxes[j][2] - cls_boxes[j][0]) * (cls_boxes[j][3] - cls_boxes[j][1])
                union = area_i + area_j - inter
                if union > 0 and inter / union > iou:
                    suppressed.add(j)

    merged = []
    for idx in keep_indices:
        merged.append({
            "x1": all_boxes[idx][0], "y1": all_boxes[idx][1],
            "x2": all_boxes[idx][2], "y2": all_boxes[idx][3],
            "cls_id": all_cls_ids[idx],
            "cls_name": all_cls_names[idx],
            "conf": all_scores[idx],
            "track_id": None,  # SAHI doesn't track — caller handles dedup
        })
    return merged


# ── Frame enhancement ─────────────────────────────────────────────────────────
_clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

def _enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    CLAHE contrast enhancement for drone footage.
    Skipped if the frame already has sufficient contrast (std > 45),
    saving ~4ms per frame on CPU.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if float(gray.std()) > 45.0:
        return frame  # already high-contrast — skip enhancement
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = _clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
    return cv2.addWeighted(enhanced, 1.4, blurred, -0.4, 0)


# ── DB helpers ────────────────────────────────────────────────────────────────
def _build_category_cache(db: Session) -> dict[str, int]:
    rows = db.execute(
        text("SELECT id, name FROM categories WHERE active = TRUE")
    ).fetchall()
    return {row.name: row.id for row in rows}


def _write_progress(db: Session, analysis_id: int, pct: int, count: int, msg: str = ""):
    db.execute(
        text("""
            UPDATE analyses
            SET total_objects = :count,
                description = CONCAT(
                    COALESCE(SPLIT_PART(COALESCE(description,''), '||PROGRESS||', 1), ''),
                    '||PROGRESS||', CAST(:pct AS TEXT),
                    '||MSG||', :msg
                )
            WHERE id = :id
        """),
        {"id": analysis_id, "count": count, "pct": pct, "msg": msg}
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

        _write_progress(db, analysis_id, 2, 0, f"Loading model for '{selected_category}'...")
        model      = _get_model_for_category(settings.YOLO_MODEL, selected_category)
        _write_progress(db, analysis_id, 4, 0, "Model loaded. Initializing pipeline...")

        SEG_CATEGORIES = {
            "trees", "plants", "water bodies", "flood water",
            "buildings", "houses", "warehouses", "shops",
        }
        if cat_key in SEG_CATEGORIES:
            _write_progress(db, analysis_id, 3, 0, "Loading SegFormer-B2 (~300MB, first run only)...")
            _get_seg_model()

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
            _write_progress(db, analysis_id, 5, 0, f"Video opened: {total_frames} frames @ {fps:.0f}fps. Starting inference...")

        # ── Tracking state ──
        confirmed_ids: set  = set()
        spatial_index: dict = {}   # spatial_key -> obj_key
        obj_screenshots: dict = {}
        first_seen_at: dict  = {}  # obj_key -> timestamp_sec

        # Proximity dedup: (center_x, center_y, cls_id) per confirmed detection
        confirmed_centers: list = []
        DEDUP_RADIUS = 60  # pixels

        # Store crops for CLIP visual dedup post-processing
        crop_store: dict = {}  # obj_key -> numpy crop array

        # Heuristic dedup dict — separate from YOLO confirmed_ids
        heuristic_seen: dict = {}

        batch: list[dict] = []
        BATCH_SIZE = 50
        raw_detection_count = 0
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
                # Save screenshot path separately if present
                if det.get("screenshot_path"):
                    db.execute(
                        text("""
                            UPDATE detections SET screenshot_path = :path
                            WHERE analysis_id = :aid AND frame_number = :fn
                            AND label = :label
                        """),
                        {
                            "path": det["screenshot_path"],
                            "aid": det["analysis_id"],
                            "fn": det["frame_number"],
                            "label": det["label"],
                        }
                    )
                raw_detection_count += 1
            db.commit()
            batch.clear()

        def process_frame(frame: np.ndarray, frame_idx: int, timestamp_sec: float):
            nonlocal raw_detection_count

            h, w = frame.shape[:2]
            enhanced = _enhance_frame(frame)

            # Use higher resolution for small-object categories
            infer_size = SMALL_OBJ_INFER_SIZE if cat_key in SAHI_CATEGORIES else 640
            if w > infer_size:
                scale = infer_size / w
                frame_small = cv2.resize(enhanced, (infer_size, int(h * scale)))
            else:
                frame_small = enhanced
            h_s, w_s = frame_small.shape[:2]

            # ── Heuristic detection for categories not in YOLO COCO ──────────────
            if cat_key in HEURISTIC_CATEGORIES:
                cat_id = cat_cache.get(target_cat)
                if cat_id is None:
                    cat_id = next(
                        (v for k, v in cat_cache.items() if k.lower() == cat_key), None
                    )
                if cat_id is not None:
                    _detect_heuristic(
                        enhanced, target_cat, frame_idx, timestamp_sec,
                        analysis_id, cat_id, chars_str,
                        heuristic_seen, obj_screenshots, batch, settings
                    )
                return  # heuristic-only, skip YOLO for this category

            # ── SAHI tiled inference ── DISABLED for CPU performance.
            # Each SAHI pass adds 4 extra YOLO inferences per frame (~5x slower).
            # The real accuracy fix was lowering MIN_DISPLAY_CONFIDENCE (0.75→0.35).
            # Enable on GPU servers for maximum recall.
            sahi_detections = None
            # if cat_key in SAHI_CATEGORIES and w >= 1280:
            #     sahi_detections = _run_sahi_tiled(
            #         model, enhanced, conf_threshold, iou_threshold
            #     )

            try:
                results = model.track(
                    frame_small,
                    persist=True,
                    verbose=False,
                    conf=conf_threshold,
                    iou=iou_threshold,
                    agnostic_nms=False,
                    max_det=300,
                    tracker="bytetrack.yaml",
                )
            except Exception:
                results = model(
                    frame_small,
                    verbose=False,
                    conf=conf_threshold,
                    iou=iou_threshold,
                    agnostic_nms=False,
                    max_det=300,
                )

            # ── Phase 1: Collect all valid detections in this frame ──
            all_frame_objects = []   # ALL detected objects (for full-frame annotation)
            new_detections = []     # only NEW unique objects (for batch + CLIP dedup)

            for result in results:
                if result.boxes is None or len(result.boxes) == 0:
                    continue

                for box in result.boxes:
                    cls_id     = int(box.cls[0])
                    cls_name   = model.names[cls_id]
                    confidence = float(box.conf[0])
                    track_id   = int(box.id[0]) if box.id is not None else None

                    # 75% confidence gate — only record high-confidence detections
                    if confidence < settings.MIN_DISPLAY_CONFIDENCE:
                        continue

                    # Scale bbox to original resolution
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    x1o = x1 * (w / w_s); y1o = y1 * (h / h_s)
                    x2o = x2 * (w / w_s); y2o = y2 * (h / h_s)

                    cls_name = _correct_aerial_misclassification(
                        cls_name, x1o, y1o, x2o, y2o, target_cat
                    )
                    if cls_name == "person":
                        cls_id = next(
                            (k for k, v in model.names.items() if v == "person"), cls_id
                        )

                    mapped_cat = YOLO_TO_CATEGORY.get(cls_name)
                    if not mapped_cat:
                        continue
                    if detection_mode != "custom" and mapped_cat.lower() != target_cat.lower():
                        continue

                    cat_id = cat_cache.get(mapped_cat)
                    if cat_id is None:
                        continue

                    crop = None
                    if 0 <= int(x1o) < w and 0 <= int(y1o) < h:
                        crop = frame[
                            max(0, int(y1o)):min(h, int(y2o)),
                            max(0, int(x1o)):min(w, int(x2o)),
                        ]
                    if not _matches_characteristics(target_cat, characteristics, cls_name, crop):
                        continue

                    # This object passed all filters — add to frame annotation list
                    all_frame_objects.append({
                        'x1': x1o, 'y1': y1o, 'x2': x2o, 'y2': y2o,
                        'cls_name': cls_name, 'conf': confidence, 'track_id': track_id,
                    })

                    # ── Unique object dedup ──
                    grid_size = 40 if cat_key in ("people", "plants") else 50
                    spatial_key = (
                        round((x1o + x2o) / 2 / grid_size),
                        round((y1o + y2o) / 2 / grid_size),
                        cls_id
                    )

                    if track_id is not None:
                        obj_key = (track_id, cls_id)
                    else:
                        obj_key = spatial_key

                    if spatial_key in spatial_index:
                        existing = spatial_index[spatial_key]
                        if existing != obj_key and existing in confirmed_ids:
                            continue

                    is_new = obj_key not in confirmed_ids

                    # Proximity dedup
                    if is_new:
                        cx_new = (x1o + x2o) / 2
                        cy_new = (y1o + y2o) / 2
                        too_close = False
                        for (cx_old, cy_old, old_cls) in confirmed_centers:
                            if old_cls == cls_id:
                                dist = ((cx_new - cx_old)**2 + (cy_new - cy_old)**2) ** 0.5
                                if dist < DEDUP_RADIUS:
                                    too_close = True
                                    break
                        if too_close:
                            confirmed_ids.add(obj_key)
                            continue

                    if is_new:
                        confirmed_ids.add(obj_key)
                        spatial_index[spatial_key] = obj_key
                        first_seen_at[obj_key] = timestamp_sec
                        confirmed_centers.append((
                            (x1o + x2o) / 2, (y1o + y2o) / 2, cls_id
                        ))

                        # Save raw crop for CLIP visual dedup (unannotated)
                        if crop is not None and crop.size > 0:
                            crop_store[obj_key] = crop.copy()

                        new_detections.append({
                            'x1': x1o, 'y1': y1o, 'x2': x2o, 'y2': y2o,
                            'cls_name': cls_name, 'conf': confidence,
                            'track_id': track_id, 'obj_key': obj_key,
                            'cat_id': cat_id, 'cls_id': cls_id,
                        })

            # ── Merge SAHI detections not already covered by ByteTrack ──
            if sahi_detections:
                for sd in sahi_detections:
                    sx1, sy1, sx2, sy2 = sd['x1'], sd['y1'], sd['x2'], sd['y2']
                    s_cls_name = sd['cls_name']
                    s_conf = sd['conf']

                    if s_conf < settings.MIN_DISPLAY_CONFIDENCE:
                        continue

                    s_cls_name = _correct_aerial_misclassification(
                        s_cls_name, sx1, sy1, sx2, sy2, target_cat
                    )
                    s_cls_id = sd['cls_id']
                    if s_cls_name == "person":
                        s_cls_id = next(
                            (k for k, v in model.names.items() if v == "person"), s_cls_id
                        )

                    mapped_cat = YOLO_TO_CATEGORY.get(s_cls_name)
                    if not mapped_cat:
                        continue
                    if detection_mode != "custom" and mapped_cat.lower() != target_cat.lower():
                        continue

                    cat_id = cat_cache.get(mapped_cat)
                    if cat_id is None:
                        continue

                    # Check if this SAHI detection overlaps with any existing detection
                    already_covered = False
                    for existing in all_frame_objects:
                        # Compute IoU
                        ix1 = max(sx1, existing['x1'])
                        iy1 = max(sy1, existing['y1'])
                        ix2 = min(sx2, existing['x2'])
                        iy2 = min(sy2, existing['y2'])
                        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
                        area_s = (sx2 - sx1) * (sy2 - sy1)
                        area_e = (existing['x2'] - existing['x1']) * (existing['y2'] - existing['y1'])
                        union = area_s + area_e - inter
                        if union > 0 and inter / union > 0.3:
                            already_covered = True
                            break
                    if already_covered:
                        continue

                    # This SAHI detection is NEW — process it
                    crop = None
                    if 0 <= int(sx1) < w and 0 <= int(sy1) < h:
                        crop = frame[
                            max(0, int(sy1)):min(h, int(sy2)),
                            max(0, int(sx1)):min(w, int(sx2)),
                        ]
                    if not _matches_characteristics(target_cat, characteristics, s_cls_name, crop):
                        continue

                    all_frame_objects.append({
                        'x1': sx1, 'y1': sy1, 'x2': sx2, 'y2': sy2,
                        'cls_name': s_cls_name, 'conf': s_conf, 'track_id': None,
                    })

                    # Unique object dedup (same as ByteTrack path)
                    grid_size = 40 if cat_key in ("people", "plants") else 50
                    spatial_key = (
                        round((sx1 + sx2) / 2 / grid_size),
                        round((sy1 + sy2) / 2 / grid_size),
                        s_cls_id
                    )
                    obj_key = spatial_key  # SAHI has no track_id

                    if spatial_key in spatial_index:
                        existing_key = spatial_index[spatial_key]
                        if existing_key != obj_key and existing_key in confirmed_ids:
                            continue

                    is_new = obj_key not in confirmed_ids
                    if is_new:
                        cx_new = (sx1 + sx2) / 2
                        cy_new = (sy1 + sy2) / 2
                        too_close = False
                        for (cx_old, cy_old, old_cls) in confirmed_centers:
                            if old_cls == s_cls_id:
                                dist = ((cx_new - cx_old)**2 + (cy_new - cy_old)**2) ** 0.5
                                if dist < DEDUP_RADIUS:
                                    too_close = True
                                    break
                        if too_close:
                            confirmed_ids.add(obj_key)
                            continue

                        confirmed_ids.add(obj_key)
                        spatial_index[spatial_key] = obj_key
                        first_seen_at[obj_key] = timestamp_sec
                        confirmed_centers.append((cx_new, cy_new, s_cls_id))

                        if crop is not None and crop.size > 0:
                            crop_store[obj_key] = crop.copy()

                        new_detections.append({
                            'x1': sx1, 'y1': sy1, 'x2': sx2, 'y2': sy2,
                            'cls_name': s_cls_name, 'conf': s_conf,
                            'track_id': None, 'obj_key': obj_key,
                            'cat_id': cat_id, 'cls_id': s_cls_id,
                        })

            # ── Phase 2: Full-frame screenshot with ALL detected objects ──
            if all_frame_objects:
                annotated = frame.copy()
                for obj in all_frame_objects:
                    ox1, oy1 = int(obj['x1']), int(obj['y1'])
                    ox2, oy2 = int(obj['x2']), int(obj['y2'])
                    cv2.rectangle(annotated, (ox1, oy1), (ox2, oy2), (57, 255, 20), 2)
                    tid = obj['track_id']
                    lbl = f"{obj['cls_name']}{'#'+str(tid) if tid else ''} {obj['conf']:.0%}"
                    cv2.putText(annotated, lbl, (ox1, max(oy1 - 6, 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (57, 255, 20), 2)
                # Frame info overlay
                info = f"T={timestamp_sec:.1f}s | {len(all_frame_objects)} detected | {len(confirmed_ids)} unique total"
                cv2.putText(annotated, info, (8, annotated.shape[0] - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

                # Save screenshot if new detections found (limit to MAX_SCREENSHOTS)
                if new_detections and len(obj_screenshots) < MAX_SCREENSHOTS * 3:
                    shot_path = _save_screenshot(annotated, f"map_{analysis_id}", timestamp_sec)
                    for det in new_detections:
                        obj_screenshots[det['obj_key']] = shot_path

            # ── Phase 3: Create batch items for new detections ──
            for det in new_detections:
                label = (
                    f"{det['cls_name']}{(' #'+str(det['track_id'])) if det['track_id'] else ''} "
                    f"({det['conf']:.0%}) first seen T={timestamp_sec:.1f}s"
                )
                batch.append({
                    "analysis_id": analysis_id,
                    "category_id": det['cat_id'],
                    "label": label,
                    "confidence": det['conf'],
                    "bbox_x": det['x1'] / w, "bbox_y": det['y1'] / h,
                    "bbox_w": (det['x2'] - det['x1']) / w,
                    "bbox_h": (det['y2'] - det['y1']) / h,
                    "frame_number": frame_idx,
                    "timestamp": timestamp_sec,
                    "characteristics": chars_str,
                    "screenshot_path": obj_screenshots.get(det['obj_key']),
                })

            if len(batch) >= BATCH_SIZE:
                flush_batch()

        # ── Main loop ──
        if is_image:
            process_frame(frame, 0, 0.0)
            flush_batch()
            _write_progress(db, analysis_id, 100, len(confirmed_ids))
        else:
            frame_idx = 0
            processed = 0
            total_sampled = max(1, total_frames // frame_interval)

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_interval == 0:
                    from ..api.v1.analysis import is_cancelled
                    if is_cancelled(analysis_id):
                        logger.info(f"[AI] Analysis {analysis_id} cancelled at frame {frame_idx}")
                        cap.release()
                        flush_batch()
                        return {"analysis_id": analysis_id, "cancelled": True}

                    process_frame(frame, frame_idx, frame_idx / fps)
                    processed += 1

                    pct = min(99, int((processed / total_sampled) * 100))
                    if pct >= last_progress + 2 or processed % 10 == 0:
                        flush_batch()
                        live_msg = f"Frame {frame_idx}/{total_frames} — {len(confirmed_ids)} unique {selected_category} found"
                        _write_progress(db, analysis_id, max(5, pct), len(confirmed_ids), live_msg)
                        last_progress = pct
                        logger.info(f"[AI] {pct}% ({processed}/{total_sampled}) | {len(confirmed_ids)} unique")

                frame_idx += 1

            cap.release()
            flush_batch()

        processing_time_before_dedup = time.time() - start_time

        # ── Post-processing: CLIP visual dedup (removes same-looking people) ──
        # Encode each person crop with CLIP, compare pairwise,
        # merge any two with similarity > 0.85 (same clothing/appearance).
        unique_count = len(confirmed_ids)  # fallback
        try:
            if len(crop_store) >= 2:
                _write_progress(db, analysis_id, 96, len(confirmed_ids),
                                "Running visual dedup (CLIP)...")

                import torch
                from transformers import CLIPProcessor, CLIPModel
                from PIL import Image as PILImage

                device = "cuda" if torch.cuda.is_available() else "cpu"
                clip_model = CLIPModel.from_pretrained(
                    "openai/clip-vit-base-patch32"
                ).to(device)
                clip_proc = CLIPProcessor.from_pretrained(
                    "openai/clip-vit-base-patch32"
                )
                clip_model.eval()

                # Encode all crops
                embeddings = {}
                obj_keys_list = []
                for obj_key, crop_img in crop_store.items():
                    if crop_img is None or crop_img.size == 0:
                        continue
                    try:
                        pil = PILImage.fromarray(
                            cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
                        )
                        with torch.no_grad():
                            inp = clip_proc(images=pil, return_tensors="pt")
                            feat = clip_model.get_image_features(
                                pixel_values=inp["pixel_values"].to(device)
                            )
                            # Handle structured output from some transformers versions
                            if not isinstance(feat, torch.Tensor):
                                feat = feat.pooler_output if hasattr(feat, 'pooler_output') else feat[0]
                            feat = feat / feat.norm(dim=-1, keepdim=True)
                            embeddings[obj_key] = feat
                            obj_keys_list.append(obj_key)
                    except Exception:
                        continue

                # Pairwise comparison: merge visually similar detections
                # RULE: NEVER merge two detections first seen at the same time
                # (same frame = guaranteed different people)
                VISUAL_SIM_THRESHOLD = 0.82
                SAME_FRAME_WINDOW = 1.5  # seconds — if first_seen within this, don't merge
                merged_away = set()
                for i in range(len(obj_keys_list)):
                    if obj_keys_list[i] in merged_away:
                        continue
                    for j in range(i + 1, len(obj_keys_list)):
                        if obj_keys_list[j] in merged_away:
                            continue
                        # Same-frame protection: don't merge co-occurring detections
                        ts_i = first_seen_at.get(obj_keys_list[i], -999)
                        ts_j = first_seen_at.get(obj_keys_list[j], -999)
                        if abs(ts_i - ts_j) < SAME_FRAME_WINDOW:
                            continue  # seen at ~same time → different objects
                        sim = float((
                            embeddings[obj_keys_list[i]] @
                            embeddings[obj_keys_list[j]].T
                        ).squeeze())
                        if sim > VISUAL_SIM_THRESHOLD:
                            merged_away.add(obj_keys_list[j])

                unique_count = len(obj_keys_list) - len(merged_away)
                if merged_away:
                    logger.info(
                        f"[AI] CLIP visual dedup: {len(obj_keys_list)} crops "
                        f"-> {unique_count} unique (merged {len(merged_away)} duplicates, "
                        f"threshold={VISUAL_SIM_THRESHOLD})"
                    )

                # Clean up CLIP from GPU memory
                del clip_model, clip_proc, embeddings
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        except Exception as e:
            logger.warning(f"[AI] CLIP visual dedup failed ({e}), using spatial count")
            # Fall back to spatial dedup
            merged_centers = []
            for (cx, cy, cid) in confirmed_centers:
                is_dup = False
                for (mx, my, mid) in merged_centers:
                    if mid == cid and ((cx-mx)**2+(cy-my)**2)**0.5 < DEDUP_RADIUS:
                        is_dup = True
                        break
                if not is_dup:
                    merged_centers.append((cx, cy, cid))
            unique_count = len(merged_centers) if merged_centers else len(confirmed_ids)

        processing_time = time.time() - start_time

        # ── Delete excess detection records from DB ──
        # During processing, all detections were flushed to the DB.
        # After CLIP dedup, unique_count may be much lower than the DB row count.
        # Keep only the top `unique_count` detections by confidence, delete the rest.
        try:
            current_det_count = db.execute(
                text("SELECT COUNT(*) FROM detections WHERE analysis_id = :id"),
                {"id": analysis_id}
            ).scalar() or 0

            if unique_count < current_det_count:
                logger.info(
                    f"[AI] Pruning detections: {current_det_count} in DB "
                    f"-> keeping top {unique_count} by confidence"
                )
                # Delete all but the top N detections (by confidence DESC)
                db.execute(
                    text("""
                        DELETE FROM detections
                        WHERE analysis_id = :id
                          AND id NOT IN (
                            SELECT id FROM detections
                            WHERE analysis_id = :id
                            ORDER BY confidence DESC
                            LIMIT :keep
                          )
                    """),
                    {"id": analysis_id, "keep": unique_count}
                )
                db.commit()
                logger.info(f"[AI] Pruned: kept {unique_count} detection records")
        except Exception as prune_err:
            logger.warning(f"[AI] Detection pruning failed: {prune_err}")

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
