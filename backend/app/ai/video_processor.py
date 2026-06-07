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
) -> Optional[np.ndarray]:
    """
    Run SegFormer-B2 on a frame and return a binary mask for the target category.
    Returns None if SegFormer is unavailable.
    """
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

# ── Model cache — load once per process, reuse across all analyses ────────────
_model_cache: dict[str, YOLO] = {}

# ── Specialist model registry ─────────────────────────────────────────────────
# Fine-tuned models override the base model for specific categories.
# Falls back to base YOLO model if specialist file is not present.
SPECIALIST_MODELS: dict[str, str] = {
    # VisDrone fine-tuned: aerial people + vehicles
    "people":             "skyrecon_visdrone.pt",
    "vehicles":           "skyrecon_visdrone.pt",
    # Road damage fine-tuned: potholes + cracks
    "road potholes":      "skyrecon_rdd2022.pt",
    # Fire/smoke fine-tuned
    "fire & smoke":       "skyrecon_fire_smoke.pt",
    # Flood fine-tuned
    "flood water":        "skyrecon_flood.pt",
    # Trees & Plants fine-tuned (train with SkyRecon_TreesPlants_Training.ipynb)
    "trees":              "skyrecon_trees_plants.pt",
    "plants":             "skyrecon_trees_plants.pt",
    # Buildings & Houses fine-tuned (train with SkyRecon_Buildings_Training.ipynb)
    "buildings":          "skyrecon_buildings.pt",
    "houses":             "skyrecon_buildings.pt",
    "warehouses":         "skyrecon_buildings.pt",
    "shops":              "skyrecon_buildings.pt",
}

def _get_model(model_path: str) -> YOLO:
    """Load and cache YOLO model. Auto-detects optimal thread count."""
    if model_path not in _model_cache:
        import torch
        cpu_count = os.cpu_count() or 4
        intra = max(1, cpu_count // 2)
        inter = max(1, cpu_count - intra)
        torch.set_num_threads(intra)
        torch.set_num_interop_threads(inter)
        logger.info(f"[AI] Loading model: {model_path} | threads={intra}+{inter}")
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
}

# ── Heuristic-only categories (not detectable via YOLO COCO classes) ──────────
# These use OpenCV image analysis instead of / in addition to YOLO.
HEURISTIC_CATEGORIES = {
    "trees", "road potholes", "water bodies", "flood water",
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
    """
    Comprehensive characteristic filtering for ALL 25 SkyRecon categories.

    Uses OpenCV heuristics (HSV colour, edge density, contour area, aspect ratio)
    to implement best-effort filtering from aerial drone footage.  Filters that
    are fundamentally impossible from altitude pass through silently (return True).
    """
    if not characteristics or not isinstance(characteristics, dict):
        return True
    # Helper: treat missing / "All" values as no-filter
    def _get(key: str) -> str:
        v = characteristics.get(key, "All")
        return v if v and v != "All" else "All"

    cat_lower = target_cat.strip().lower()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  1. VEHICLES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if cat_lower == "vehicles":
        vehicle_type = _get("type")
        if vehicle_type != "All" and cls_name is not None:
            vehicle_filters = {
                "Light Vehicle (Sedan/SUV)": {"car"},
                "Heavy Vehicle (Truck/Bus)": {"truck", "bus"},
                "2-Wheeler": {"motorcycle", "bicycle"},
                "3-Wheeler": {"motorcycle", "bicycle"},
                "4-Wheeler": {"car", "truck", "bus"},
                "6-Wheeler": {"truck", "bus"},
                "Bike": {"bicycle", "motorcycle"},
                "Scooty": {"motorcycle", "bicycle"},
                "Car": {"car"},
                "Bus": {"bus"},
                "Truck": {"truck"},
                "Ambulance": {"truck", "car"},  # YOLO doesn't separate ambulance
                "Police Vehicle": {"car"},
            }
            allowed = vehicle_filters.get(vehicle_type, {cls_name})
            if cls_name not in allowed:
                return False
        vehicle_color = _get("color")
        if vehicle_color != "All" and crop is not None:
            detected_color = _infer_color_label(crop)
            if detected_color != vehicle_color:
                return False
        # Movement: requires temporal analysis — pass through
        # Structural damage: approximate via edge chaos
        damaged = _get("damaged")
        if damaged != "All" and crop is not None:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            if damaged == "Damaged" and edge_density < 0.12:
                return False
            if damaged == "Undamaged" and edge_density > 0.25:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  2. PEOPLE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "people":
        # Gender / Age: best-effort from body size
        gender = _get("gender")
        if gender != "All" and crop is not None:
            h_crop, w_crop = crop.shape[:2]
            area = h_crop * w_crop
            if gender == "Child" and area > 2500:
                return False  # children are smaller blobs from aerial
            if gender == "Elderly":
                pass  # not distinguishable from altitude
            if gender == "Worker":
                # workers typically wear bright safety gear
                yellow_r = _region_hsv_ratio(crop, [18, 100, 100], [35, 255, 255])
                orange_r = _region_hsv_ratio(crop, [10, 100, 100], [20, 255, 255])
                if (yellow_r + orange_r) < 0.08:
                    return False
            # Male / Female: approximate via dominant clothing colour distribution
            # Upper body colour tends to differ statistically but is unreliable
            # from >30m altitude — we apply a loose heuristic
            if gender in ("Male", "Female"):
                # Darker, cooler clothing → Male bias; brighter, warmer → Female bias
                # This is ~55% accurate at best — intentional loose filter
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                mean_s = float(np.mean(hsv[:, :, 1]))
                mean_v = float(np.mean(hsv[:, :, 2]))
                if gender == "Male" and mean_s > 120 and mean_v > 180:
                    return False  # very bright saturated clothing → skip
                if gender == "Female" and mean_s < 30 and mean_v < 80:
                    return False  # very dark desaturated clothing → skip

        # Clothing Colour
        clothing_color = _get("clothingColor")
        if clothing_color != "All" and crop is not None:
            detected_color = _infer_color_label(crop)
            if detected_color != clothing_color:
                return False

        # Safety Equipment
        safety = _get("safety")
        if safety != "All" and crop is not None:
            yellow_r = _region_hsv_ratio(crop, [18, 100, 100], [35, 255, 255])
            orange_r = _region_hsv_ratio(crop, [10, 100, 100], [20, 255, 255])
            has_bright_gear = (yellow_r + orange_r) > 0.12
            # Helmet: bright/white region in top quarter of crop
            h_crop = crop.shape[0]
            top_quarter = crop[:max(1, h_crop // 4), :]
            helmet_bright = 0.0
            if top_quarter.size > 0:
                white_r = _region_hsv_ratio(top_quarter, [0, 0, 180], [180, 60, 255])
                yellow_top = _region_hsv_ratio(top_quarter, [18, 80, 100], [35, 255, 255])
                helmet_bright = white_r + yellow_top

            if safety == "Helmet Detected" and helmet_bright < 0.08:
                return False
            if safety == "Safety Jacket Detected" and not has_bright_gear:
                return False
            if safety == "Both Detected" and (not has_bright_gear or helmet_bright < 0.08):
                return False
            if safety == "No Equipment" and (has_bright_gear or helmet_bright > 0.12):
                return False

        # Activity State — bounding box aspect ratio
        activity = _get("activity")
        if activity != "All" and crop is not None:
            h_crop, w_crop = crop.shape[:2]
            aspect = w_crop / max(h_crop, 1)  # width / height
            if activity == "Standing" and aspect > 1.8:
                return False  # standing person is tall (narrow bbox)
            if activity == "Sitting" and (aspect < 0.5 or aspect > 2.5):
                return False  # sitting person is roughly square
            if activity == "Lying" and aspect < 1.4:
                return False  # lying person is wide bbox

        # Crowd Density — handled at aggregation level, not per-detection
        # pass through here; density is computed post-counting

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  3. PLANTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "plants":
        plant_type = _get("type")
        if plant_type != "All" and crop is not None:
            area = crop.shape[0] * crop.shape[1]
            if plant_type == "Potted plants" and area > 8000:
                return False
            if plant_type == "Small plants" and (area < 500 or area > 20000):
                return False
            if plant_type == "Medium plants" and area < 8000:
                return False
            if plant_type == "Dense vegetation" and area < 25000:
                return False
        empty_soil = _get("emptySoil")
        if empty_soil != "All" and crop is not None:
            green_r = _region_hsv_ratio(crop, [25, 40, 40], [95, 255, 255])
            brown_r = _region_hsv_ratio(crop, [8, 30, 40], [25, 180, 180])
            if empty_soil == "Empty soil detected" and brown_r < 0.15:
                return False
            if empty_soil == "Fully covered" and green_r < 0.50:
                return False
        # Area estimate: pass through (requires GSD calculation)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  4. TREES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "trees":
        tree_health = _get("health")
        if tree_health != "All" and crop is not None:
            green_ratio = _region_hsv_ratio(crop, [25, 40, 40], [95, 255, 255])
            if tree_health == "Healthy Green" and green_ratio < 0.5:
                return False
            if tree_health == "Diseased/Dry" and green_ratio > 0.45:
                return False
            if tree_health == "Deactivated canopy" and green_ratio > 0.25:
                return False
        tree_type = _get("type")
        if tree_type != "All" and crop is not None:
            area = crop.shape[0] * crop.shape[1]
            if tree_type == "Large trees" and area < 16000:
                return False
            if tree_type == "Dry trees":
                green_ratio = _region_hsv_ratio(crop, [25, 40, 40], [95, 255, 255])
                if green_ratio > 0.45:
                    return False
            if tree_type == "Dense forest canopy" and area < 40000:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  5. ELECTRIC POLES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "electric poles":
        pole_type = _get("type")
        if pole_type != "All" and crop is not None:
            # Wood is brownish, metal is greyish, concrete is light grey
            brown_r = _region_hsv_ratio(crop, [8, 30, 40], [25, 180, 180])
            gray_r = _region_hsv_ratio(crop, [0, 0, 80], [180, 40, 200])
            if pole_type == "Wooden Utility Pole" and brown_r < 0.10:
                return False
            if pole_type == "Metal Utility Pole" and gray_r < 0.15:
                return False
            if pole_type == "Reinforced Concrete Pole" and gray_r < 0.20:
                return False
        danger = _get("danger")
        if danger != "All" and crop is not None:
            h_crop, w_crop = crop.shape[:2]
            aspect = h_crop / max(w_crop, 1)
            # Vertical pole: aspect >> 1; leaning: lower aspect
            if danger == "Stable Vertical" and aspect < 3.0:
                return False
            if danger == "Listing (Leaning >15°)" and (aspect > 5.0 or aspect < 1.5):
                return False
            if danger == "Severely Damaged / Snapped" and aspect > 3.0:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  6. TRAFFIC LIGHTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "traffic lights":
        state = _get("state")
        if state != "All" and crop is not None:
            mean_v = float(np.mean(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]))
            if state == "Active Operating" and mean_v < 80:
                return False
            if state == "Inactive/Blank" and mean_v > 120:
                return False
        sig_color = _get("signalColor")
        if sig_color != "All" and crop is not None:
            red_r = _region_hsv_ratio(crop, [0, 100, 100], [10, 255, 255])
            red_r2 = _region_hsv_ratio(crop, [160, 100, 100], [180, 255, 255])
            yellow_r = _region_hsv_ratio(crop, [18, 100, 100], [35, 255, 255])
            green_r = _region_hsv_ratio(crop, [40, 80, 80], [85, 255, 255])
            if sig_color == "Red Signal" and (red_r + red_r2) < 0.05:
                return False
            if sig_color == "Yellow Signal" and yellow_r < 0.05:
                return False
            if sig_color == "Green Signal" and green_r < 0.05:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  7. ROADS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "roads":
        road_type = _get("type")
        if road_type != "All" and crop is not None:
            gray_r = _region_hsv_ratio(crop, [0, 0, 60], [180, 40, 180])
            brown_r = _region_hsv_ratio(crop, [8, 30, 40], [25, 180, 180])
            if road_type == "Asphalt Paved" and gray_r < 0.20:
                return False
            if road_type == "Concrete Paved" and gray_r < 0.25:
                return False
            if road_type == "Unpaved Dirt Road" and brown_r < 0.15:
                return False
        road_state = _get("state")
        if road_state != "All" and crop is not None:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            if road_state == "Excellent" and edge_density > 0.10:
                return False
            if road_state == "Damaged surface" and edge_density < 0.06:
                return False
            if road_state == "Severe blockages" and edge_density < 0.12:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  8. ROAD POTHOLES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "road potholes":
        severity = _get("severity")
        if severity != "All" and crop is not None:
            area = crop.shape[0] * crop.shape[1]
            if severity == "Minor Crack" and area > 5000:
                return False
            if severity == "Moderate Pothole" and (area < 2000 or area > 30000):
                return False
            if severity == "Severe Pothole Crater" and area < 10000:
                return False
        moisture = _get("moisture")
        if moisture != "All" and crop is not None:
            blue_r = _region_hsv_ratio(crop, [90, 30, 30], [140, 255, 255])
            if moisture == "Water-filled Pothole" and blue_r < 0.08:
                return False
            if moisture == "Dry Pothole" and blue_r > 0.15:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  9. WATER BODIES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "water bodies":
        wb_type = _get("type")
        if wb_type != "All" and crop is not None:
            area = crop.shape[0] * crop.shape[1]
            if wb_type == "Puddle/Water Logging" and area > 30000:
                return False
            if wb_type == "Pond" and (area < 10000 or area > 200000):
                return False
            if wb_type == "Lake" and area < 80000:
                return False
            # Canal: elongated shape
            if wb_type == "Canal/Drainage":
                aspect = crop.shape[1] / max(crop.shape[0], 1)
                if 0.4 < aspect < 2.5:  # not elongated enough
                    return False
        spread = _get("spread")
        if spread != "All" and crop is not None:
            area = crop.shape[0] * crop.shape[1]
            if spread == "Minor localized" and area > 20000:
                return False
            if spread == "Significant spread" and (area < 10000 or area > 100000):
                return False
            if spread == "Widespread overflow" and area < 50000:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 10. BUILDINGS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "buildings":
        bldg_type = _get("type")
        if bldg_type != "All" and crop is not None:
            area = crop.shape[0] * crop.shape[1]
            if bldg_type == "Residential Block" and area > 100000:
                return False
            if bldg_type == "Industrial Complex" and area < 40000:
                return False
            # Commercial: pass through (hard to distinguish from aerial)
        bldg_state = _get("state")
        if bldg_state != "All" and crop is not None:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 40, 120)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            # Damaged structures have more chaotic edge patterns
            if bldg_state == "Undamaged Structure" and edge_density > 0.18:
                return False
            if bldg_state == "Cracked Walls" and edge_density < 0.08:
                return False
            if bldg_state == "Structural Collapse" and edge_density < 0.15:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 11. HOUSES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "houses":
        # Type: pass through (single vs multi from aerial is ambiguous)
        roof = _get("roof")
        if roof != "All" and crop is not None:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 40, 120)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            # Tin roof: high-frequency reflectance pattern
            tin_r = _region_hsv_ratio(crop, [0, 0, 150], [180, 30, 255])
            if roof == "Intact Roof" and edge_density > 0.15:
                return False
            if roof == "Damaged roof" and edge_density < 0.08:
                return False
            if roof == "Tin roof collapsed" and (tin_r < 0.10 or edge_density < 0.12):
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 12. PARKING AREAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "parking areas":
        # Type: pass through (covered vs open hard from straight-down view)
        utilization = _get("utilization")
        if utilization != "All" and crop is not None:
            # Parking occupancy: ratio of non-grey (vehicle-coloured) pixels
            gray_r = _region_hsv_ratio(crop, [0, 0, 60], [180, 35, 200])
            vehicle_ratio = 1.0 - gray_r
            if utilization == "Empty slots (<10%)" and vehicle_ratio > 0.20:
                return False
            if utilization == "Moderate (10%-70%)" and (vehicle_ratio < 0.10 or vehicle_ratio > 0.70):
                return False
            if utilization == "Full slots (>70%)" and vehicle_ratio < 0.50:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 13. GARBAGE AREAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "garbage areas":
        state = _get("state")
        if state != "All" and crop is not None:
            area = crop.shape[0] * crop.shape[1]
            if state == "Under control" and area > 30000:
                return False
            if state == "Overflowing Trash" and area < 8000:
                return False
        composition = _get("composition")
        if composition != "All" and crop is not None:
            green_r = _region_hsv_ratio(crop, [25, 40, 40], [95, 255, 255])
            blue_r = _region_hsv_ratio(crop, [90, 40, 40], [140, 255, 255])
            if composition == "Organic waste" and green_r < 0.08:
                return False
            if composition == "Recyclable materials" and blue_r < 0.05:
                return False
            # Hazardous: pass through (impossible from visual alone)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 14. CONSTRUCTION ZONES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "construction zones":
        stage = _get("stage")
        if stage != "All" and crop is not None:
            brown_r = _region_hsv_ratio(crop, [8, 40, 60], [28, 200, 220])
            gray_r = _region_hsv_ratio(crop, [0, 0, 80], [180, 40, 200])
            edges = cv2.Canny(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 40, 120)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            if stage == "Excavation phase" and brown_r < 0.15:
                return False
            if stage == "Structural framing" and edge_density < 0.08:
                return False
            if stage == "Finishing work" and gray_r < 0.15:
                return False
        status = _get("status")
        if status != "All" and crop is not None:
            yellow_r = _region_hsv_ratio(crop, [18, 100, 100], [35, 255, 255])
            if status == "Active working" and yellow_r < 0.03:
                return False
            if status == "Inactive/Abandoned" and yellow_r > 0.10:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 15. AGRICULTURAL LAND
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "agricultural land":
        status = _get("status")
        if status != "All" and crop is not None:
            green_r = _region_hsv_ratio(crop, [30, 40, 40], [90, 255, 200])
            brown_r = _region_hsv_ratio(crop, [8, 30, 40], [25, 180, 180])
            if status == "Planted/Green Crop fields" and green_r < 0.25:
                return False
            if status == "Fallow/Bare land" and brown_r < 0.20:
                return False
            if status == "Harvested state" and (green_r > 0.40 or brown_r < 0.10):
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 16. ANIMALS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "animals":
        animal_type = _get("type")
        if animal_type != "All" and cls_name is not None:
            livestock = {"cow", "sheep", "horse"}
            wild = {"elephant", "bear", "zebra", "giraffe"}
            strays = {"dog", "cat"}
            if animal_type == "Livestock (Cows/Goats)" and cls_name not in livestock:
                return False
            if animal_type == "Wild animals" and cls_name not in wild:
                return False
            if animal_type == "Stray dogs/cats" and cls_name not in strays:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 17. SOLAR PANELS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "solar panels":
        sp_type = _get("type")
        if sp_type != "All" and crop is not None:
            # Rooftop panels are smaller, ground mounts are larger arrays
            area = crop.shape[0] * crop.shape[1]
            if sp_type == "Rooftop Mount" and area > 80000:
                return False
            if sp_type == "Ground Mount Grid" and area < 20000:
                return False
        sp_state = _get("state")
        if sp_state != "All" and crop is not None:
            # Clean panels have uniform dark blue reflectance
            blue_r = _region_hsv_ratio(crop, [100, 40, 20], [140, 255, 120])
            mean_v = float(np.mean(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]))
            if sp_state == "Clean & Active" and blue_r < 0.20:
                return False
            if sp_state == "Dust covered" and mean_v > 100:
                return False
            if sp_state == "Damaged Panel":
                edges = cv2.Canny(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 50, 150)
                if np.count_nonzero(edges) / max(1, edges.size) < 0.10:
                    return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 18. BRIDGES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "bridges":
        # Type: pass through (beam vs arch vs suspension is ML-level classification)
        integrity = _get("integrity")
        if integrity != "All" and crop is not None:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 40, 120)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            if integrity == "Intact Structure" and edge_density > 0.18:
                return False
            if integrity == "Cracked Piers" and edge_density < 0.06:
                return False
            if integrity == "Severely Damaged" and edge_density < 0.12:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 19. RAILWAY TRACKS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "railway tracks":
        # Status: pass through (active vs siding not distinguishable from aerial)
        obstruction = _get("obstruction")
        if obstruction != "All" and crop is not None:
            # Obstructed tracks have more non-rail-colour pixels
            gray_r = _region_hsv_ratio(crop, [0, 0, 40], [180, 50, 160])
            if obstruction == "Clear Track" and gray_r < 0.30:
                return False
            if obstruction == "Obstruction detected" and gray_r > 0.60:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 20. FIRE & SMOKE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "fire & smoke":
        intensity = _get("intensity")
        if intensity != "All" and crop is not None:
            fire_r = _region_hsv_ratio(crop, [0, 100, 150], [25, 255, 255])
            smoke_r = _region_hsv_ratio(crop, [0, 0, 160], [180, 40, 255])
            total_r = fire_r + smoke_r
            if intensity == "Light smoke" and (fire_r > 0.05 or smoke_r < 0.03):
                return False
            if intensity == "Dense smoke" and smoke_r < 0.10:
                return False
            if intensity == "Active open fire" and fire_r < 0.08:
                return False
            if intensity == "Severe wildfire" and total_r < 0.25:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 21. FLOOD WATER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "flood water":
        level = _get("level")
        if level != "All" and crop is not None:
            area = crop.shape[0] * crop.shape[1]
            blue_r = _region_hsv_ratio(crop, [90, 30, 30], [140, 255, 255])
            if level == "Minor puddle" and area > 15000:
                return False
            if level == "Moderate overflow" and (area < 5000 or area > 80000):
                return False
            if level == "Severe deep flood" and area < 30000:
                return False
        hazard = _get("hazard")
        if hazard != "All" and crop is not None:
            area = crop.shape[0] * crop.shape[1]
            blue_r = _region_hsv_ratio(crop, [90, 30, 30], [140, 255, 255])
            if hazard == "Emergency evacuation required" and (area < 20000 or blue_r < 0.15):
                return False
            if hazard == "Normal vigilance" and area > 60000:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 22. SHOPS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "shops":
        state = _get("state")
        if state != "All" and crop is not None:
            mean_v = float(np.mean(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]))
            edges = cv2.Canny(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 40, 120)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            if state == "Open for business" and mean_v < 80:
                return False
            if state == "Closed" and mean_v > 150:
                return False
            if state == "Damaged facade" and edge_density < 0.10:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 23. WAREHOUSES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "warehouses":
        state = _get("state")
        if state != "All" and crop is not None:
            mean_v = float(np.mean(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]))
            edges = cv2.Canny(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 40, 120)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            if state == "Active facility" and mean_v < 60:
                return False
            if state == "Inactive facility" and mean_v > 140:
                return False
            if state == "Damaged roof" and edge_density < 0.10:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 24. PIPELINES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "pipelines":
        # Type: above/below ground — below ground is not visible from aerial
        pipe_type = _get("type")
        if pipe_type == "Below ground pipeline":
            return False  # cannot detect underground from drone
        safety_check = _get("safety")
        if safety_check != "All" and crop is not None:
            # Leakage: look for discolouration / wet patches around pipeline
            brown_r = _region_hsv_ratio(crop, [8, 30, 40], [25, 180, 180])
            blue_r = _region_hsv_ratio(crop, [90, 30, 30], [140, 255, 255])
            if safety_check == "Secure/Intact" and blue_r > 0.10:
                return False
            if safety_check == "Leakage suspected" and blue_r < 0.05:
                return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 25. STREET LIGHTS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif cat_lower == "street lights":
        state = _get("state")
        if state != "All" and crop is not None:
            mean_v = float(np.mean(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]))
            edges = cv2.Canny(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), 50, 150)
            edge_density = np.count_nonzero(edges) / max(1, edges.size)
            if state == "Active glowing" and mean_v < 100:
                return False
            if state == "Inactive/Dark" and mean_v > 130:
                return False
            if state == "Physically damaged" and edge_density < 0.10:
                return False

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
# People from aerial view need lower confidence + higher fps to catch walkers
CATEGORY_SETTINGS: dict[str, dict] = {
    # Aerial-view people are tiny (10-30px) — very low conf needed to catch them
    "people":             {"fps": 3, "conf": 0.22, "iou": 0.35},
    # Vehicles are large from above — higher conf reduces road-marking false positives
    "vehicles":           {"fps": 1, "conf": 0.42, "iou": 0.50},
    "animals":            {"fps": 2, "conf": 0.20, "iou": 0.40},
    # Fire/smoke: low conf to catch early-stage events
    "fire & smoke":       {"fps": 3, "conf": 0.25, "iou": 0.38},
    "flood water":        {"fps": 2, "conf": 0.28, "iou": 0.50},
    "water bodies":       {"fps": 1, "conf": 0.28, "iou": 0.50},
    "trees":              {"fps": 1, "conf": 0.28, "iou": 0.50},
    "plants":             {"fps": 1, "conf": 0.28, "iou": 0.50},
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

        model      = _get_model_for_category(settings.YOLO_MODEL, selected_category)
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
            # Check if the codec supports random seek (avoids decoding skipped frames)
            _supports_seek = cap.get(cv2.CAP_PROP_POS_FRAMES) >= 0
            logger.info(f"[AI] {total_frames} frames @ {fps:.1f}fps, interval={frame_interval}, seek={_supports_seek}")

        # ── Tracking state ──
        # confirmed_ids: set of unique object keys actually counted
        # spatial_index: maps spatial_key -> track_key, for dedup when track_id resets
        confirmed_ids: set  = set()
        spatial_index: dict = {}   # spatial_key -> obj_key
        obj_screenshots: dict = {}
        first_seen_at: dict  = {}  # obj_key -> timestamp_sec

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

            if w > 640:
                scale = 640 / w
                frame_small = cv2.resize(enhanced, (640, int(h * scale)))
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

            for result in results:
                if result.boxes is None or len(result.boxes) == 0:
                    continue

                for box in result.boxes:
                    cls_id     = int(box.cls[0])
                    cls_name   = model.names[cls_id]
                    confidence = float(box.conf[0])
                    track_id   = int(box.id[0]) if box.id is not None else None

                    # Scale bbox to original resolution
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    x1o = x1 * (w / w_s); y1o = y1 * (h / h_s)
                    x2o = x2 * (w / w_s); y2o = y2 * (h / h_s)

                    # ── Fix 1: Correct aerial misclassifications ──
                    # e.g. person from above/behind detected as kite, frisbee, etc.
                    cls_name = _correct_aerial_misclassification(
                        cls_name, x1o, y1o, x2o, y2o, target_cat
                    )
                    # Re-get cls_id after potential remap
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

                    # ── Unique object dedup ──
                    # Build spatial key on a 50px grid (tighter than before)
                    spatial_key = (
                        round((x1o + x2o) / 2 / 50),  # centre-x bucket
                        round((y1o + y2o) / 2 / 50),  # centre-y bucket
                        cls_id
                    )

                    if track_id is not None:
                        obj_key = (track_id, cls_id)
                    else:
                        obj_key = spatial_key

                    # If spatial position was already registered to a different obj_key, skip
                    if spatial_key in spatial_index:
                        existing = spatial_index[spatial_key]
                        if existing != obj_key and existing in confirmed_ids:
                            continue

                    is_first_appearance = obj_key not in confirmed_ids

                    if is_first_appearance:
                        confirmed_ids.add(obj_key)
                        spatial_index[spatial_key] = obj_key
                        first_seen_at[obj_key] = timestamp_sec

                        # ── Fix 2: Save one screenshot per NEW unique object ──
                        # Crop tightly around the detected object with padding,
                        # draw bbox + label + timestamp, save as individual screenshot.
                        try:
                            pad = 30
                            cx1 = max(0, int(x1o) - pad)
                            cy1 = max(0, int(y1o) - pad)
                            cx2 = min(w, int(x2o) + pad)
                            cy2 = min(h, int(y2o) + pad)
                            crop = frame[cy1:cy2, cx1:cx2].copy()

                            # Draw bbox on crop (offset by crop origin)
                            bx1 = int(x1o) - cx1
                            by1 = int(y1o) - cy1
                            bx2 = int(x2o) - cx1
                            by2 = int(y2o) - cy1
                            cv2.rectangle(crop, (bx1, by1), (bx2, by2), (57, 255, 20), 2)
                            tid_str = f" #{track_id}" if track_id else ""
                            cv2.putText(crop,
                                        f"{cls_name}{tid_str} {confidence:.0%}",
                                        (bx1, max(by1 - 6, 10)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (57, 255, 20), 2)
                            # Timestamp at bottom
                            cv2.putText(crop,
                                        f"T={timestamp_sec:.1f}s",
                                        (6, crop.shape[0] - 8),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2)

                            shot_path = _save_screenshot(
                                crop, f"map_{analysis_id}", timestamp_sec
                            )
                            obj_screenshots[obj_key] = shot_path
                        except Exception as se:
                            logger.debug(f"[AI] Screenshot failed: {se}")

                        label = (
                            f"{cls_name}{(' #'+str(track_id)) if track_id else ''} "
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
                            "screenshot_path": obj_screenshots.get(obj_key),
                        })

            if len(batch) >= BATCH_SIZE:
                flush_batch()

        # ── Main loop ──
        if is_image:
            process_frame(frame, 0, 0.0)
            flush_batch()
            _write_progress(db, analysis_id, 100, len(confirmed_ids))
        else:
            # Use seek-based iteration to skip decoding of unwanted frames
            sampled_indices = range(0, total_frames, frame_interval)
            for frame_idx in sampled_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break

                # Check if cancelled by user
                from ..api.v1.analysis import is_cancelled
                if is_cancelled(analysis_id):
                    logger.info(f"[AI] Analysis {analysis_id} cancelled by user at frame {frame_idx}")
                    cap.release()
                    flush_batch()
                    return {"analysis_id": analysis_id, "cancelled": True}

                process_frame(frame, frame_idx, frame_idx / fps)

                if total_frames > 0:
                    pct = min(99, int((frame_idx / total_frames) * 100))
                    if pct >= last_progress + 5:
                        flush_batch()
                        _write_progress(db, analysis_id, pct, len(confirmed_ids))
                        last_progress = pct
                        logger.info(
                            f"[AI] {pct}% | {len(confirmed_ids)} unique objects tracked"
                        )

            cap.release()
            flush_batch()

        processing_time = time.time() - start_time
        unique_count = len(confirmed_ids)

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
