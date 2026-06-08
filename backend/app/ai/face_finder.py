"""
SkyRecon – Facial Attribute Search Engine
Detects people in drone footage and filters by facial/clothing attributes using CLIP.
"""

import cv2
import base64
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def scan_video_facial_attributes(
    video_path: str,
    attributes: dict,
    target_image_bytes: Optional[bytes] = None,
) -> dict:
    """
    Scan video for people matching given facial/clothing attributes.
    Uses YOLO person detection + CLIP attribute matching.
    """
    import torch
    from PIL import Image as PILImage
    import io
    from transformers import CLIPProcessor, CLIPModel
    from ultralytics import YOLO

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load CLIP
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    clip_proc  = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    # Load YOLO for person detection
    yolo = YOLO("yolov8s.pt")

    # Build text prompts from attributes
    prompts = _build_prompts(attributes)

    # Encode target face if provided
    target_feat = None
    if target_image_bytes:
        try:
            target_pil = PILImage.open(io.BytesIO(target_image_bytes)).convert("RGB")
            with torch.no_grad():
                t_in = clip_proc(images=target_pil, return_tensors="pt")
                target_feat = clip_model.get_image_features(pixel_values=t_in["pixel_values"].to(device))
                target_feat = target_feat / target_feat.norm(dim=-1, keepdim=True)
        except Exception as e:
            logger.warning(f"[FaceFinder] Could not encode target image: {e}")

    # Encode text prompts
    text_feats = None
    if prompts:
        with torch.no_grad():
            t_in = clip_proc(text=prompts, return_tensors="pt", padding=True).to(device)
            text_feats = clip_model.get_text_features(**t_in)
            text_feats = text_feats / text_feats.norm(dim=-1, keepdim=True)

    FRAME_INTERVAL = 15
    SIMILARITY_THRESHOLD = 0.22
    matches = []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"matches": [], "total_scanned": 0, "search_mode": "facial"}

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % FRAME_INTERVAL == 0:
            timestamp = frame_idx / fps
            results = yolo(frame, verbose=False, conf=0.25, classes=[0])  # class 0 = person

            for result in results:
                if result.boxes is None:
                    continue
                for box in result.boxes:
                    x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
                    crop = frame[max(0,y1):y2, max(0,x1):x2]
                    if crop.size == 0:
                        continue

                    crop_pil = PILImage.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                    with torch.no_grad():
                        c_in = clip_proc(images=crop_pil, return_tensors="pt")
                        crop_feat = clip_model.get_image_features(pixel_values=c_in["pixel_values"].to(device))
                        crop_feat = crop_feat / crop_feat.norm(dim=-1, keepdim=True)

                    score = 0.0
                    # Score against text prompts
                    if text_feats is not None:
                        sims = (crop_feat @ text_feats.T).squeeze()
                        score = float(sims.max() if sims.dim() > 0 else sims)

                    # Score against reference face
                    if target_feat is not None:
                        face_sim = float((crop_feat @ target_feat.T).squeeze())
                        score = max(score, face_sim)

                    if score >= SIMILARITY_THRESHOLD:
                        _, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        thumb = "data:image/jpeg;base64," + base64.b64encode(buf).decode()
                        matches.append({
                            "timestamp":   round(timestamp, 2),
                            "confidence":  round(score, 3),
                            "description": f"Match at {int(timestamp//60):02d}:{int(timestamp%60):02d} — score {score:.0%}",
                            "thumbnail":   thumb,
                        })

        frame_idx += 1

    cap.release()
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return {"matches": matches, "total_scanned": frame_idx, "search_mode": "facial"}


def _build_prompts(attributes: dict) -> list[str]:
    parts = []
    gender = attributes.get("gender", "All")
    if gender and gender != "All":
        parts.append(f"a {gender.lower()} person")

    clothing = attributes.get("clothingColor", "All")
    if clothing and clothing != "All":
        parts.append(f"wearing {clothing.lower()} clothing")

    hair = attributes.get("hairColor", "All")
    if hair and hair != "All":
        parts.append(f"with {hair.lower()} hair")

    if not parts:
        return ["a person"]
    return [" ".join(parts)]
