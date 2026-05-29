"""
SkyRecon – Area & Coverage Calculator
Estimates real-world area coverage from bounding box detections.
Uses drone altitude metadata when available, otherwise uses frame-ratio estimation.
"""

from typing import Optional


# Approximate GSD (Ground Sampling Distance) in meters/pixel at common altitudes
# GSD = (sensor_width * altitude) / (focal_length * image_width)
# We use a lookup table for common DJI drone altitudes as defaults.
GSD_BY_ALTITUDE: dict[int, float] = {
    30:  0.008,   # 30m  → ~0.8 cm/pixel
    50:  0.013,   # 50m  → ~1.3 cm/pixel
    100: 0.026,   # 100m → ~2.6 cm/pixel
    120: 0.031,   # 120m → ~3.1 cm/pixel (DJI legal limit)
    150: 0.039,   # 150m → ~3.9 cm/pixel
    200: 0.052,   # 200m → ~5.2 cm/pixel
}

DEFAULT_ALTITUDE_M = 100  # assume 100m if not specified


def get_gsd(altitude_m: Optional[float] = None) -> float:
    """Returns Ground Sampling Distance (m/pixel) for a given altitude."""
    alt = altitude_m or DEFAULT_ALTITUDE_M
    # Find nearest altitude in lookup table
    nearest = min(GSD_BY_ALTITUDE.keys(), key=lambda k: abs(k - alt))
    return GSD_BY_ALTITUDE[nearest]


def bbox_to_area_sqm(
    bbox_w_norm: float,
    bbox_h_norm: float,
    frame_width_px: int,
    frame_height_px: int,
    altitude_m: Optional[float] = None,
) -> float:
    """
    Converts a normalized bounding box to real-world area in square meters.

    Args:
        bbox_w_norm: normalized bbox width (0-1)
        bbox_h_norm: normalized bbox height (0-1)
        frame_width_px: video frame width in pixels
        frame_height_px: video frame height in pixels
        altitude_m: drone altitude in meters (optional)

    Returns:
        Estimated area in square meters
    """
    gsd = get_gsd(altitude_m)
    bbox_w_px = bbox_w_norm * frame_width_px
    bbox_h_px = bbox_h_norm * frame_height_px
    area_sqm = (bbox_w_px * gsd) * (bbox_h_px * gsd)
    return round(area_sqm, 2)


def compute_coverage_stats(
    detections: list[dict],
    frame_width_px: int = 1920,
    frame_height_px: int = 1080,
    altitude_m: Optional[float] = None,
) -> dict:
    """
    Given a list of detection dicts (with bbox_w, bbox_h normalized),
    computes aggregate coverage statistics.

    Returns:
        {
            total_count: int,
            total_area_sqm: float,
            avg_area_sqm: float,
            coverage_percent: float,   # % of surveyed frame area covered
            empty_area_sqm: float,     # estimated plantable/usable remaining area
        }
    """
    if not detections:
        return {
            "total_count": 0,
            "total_area_sqm": 0.0,
            "avg_area_sqm": 0.0,
            "coverage_percent": 0.0,
            "empty_area_sqm": 0.0,
        }

    gsd = get_gsd(altitude_m)
    total_frame_area_sqm = (frame_width_px * gsd) * (frame_height_px * gsd)

    total_area = 0.0
    for det in detections:
        w = det.get("bbox_w") or 0.0
        h = det.get("bbox_h") or 0.0
        total_area += bbox_to_area_sqm(w, h, frame_width_px, frame_height_px, altitude_m)

    # Cap at 100% of frame
    coverage_ratio = min(1.0, total_area / total_frame_area_sqm) if total_frame_area_sqm > 0 else 0.0
    empty_area = max(0.0, total_frame_area_sqm - total_area)

    return {
        "total_count": len(detections),
        "total_area_sqm": round(total_area, 1),
        "avg_area_sqm": round(total_area / len(detections), 2),
        "coverage_percent": round(coverage_ratio * 100, 1),
        "empty_area_sqm": round(empty_area, 1),
    }
