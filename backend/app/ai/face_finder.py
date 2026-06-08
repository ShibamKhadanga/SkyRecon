"""
SkyRecon – Facial Attribute Object Finder
Detects persons in video frames, extracts face/upper-body crops,
and matches against selected facial attributes (and optional reference photo) via CLIP.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Optional

import cv2
import numpy as np
from PIL import Image as PILImage

from ..core.config import settings
from .video_processor import _get_model

logger = logging.getLogger(__name__)

# OpenCV Haar cascade (bundled with opencv-python-headless)
_FACE_CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# Attribute options → natural-language CLIP prompts
ATTRIBUTE_PROMPTS = {
    "gender": {
        "male": "a male person",
        "female": "a female person",
    },
    "age_group": {
        "child": "a young child",
        "teen": "a teenager",
        "adult": "an adult person",
        "elderly": "an elderly person",
    },
    "hair_color": {
        "black": "a person with black hair",
        "brown": "a person with brown hair",
        "blonde": "a person with blonde hair",
        "gray": "a person with gray or white hair",
        "red": "a person with red hair",
    },
    "facial_hair": {
        "none": "a clean-shaven person without facial hair",
        "beard": "a person with a beard",
        "mustache": "a person with a mustache",
    },
    "glasses": {
        "yes": "a person wearing eyeglasses",
        "no": "a person without eyeglasses",
    },
    "skin_tone": {
        "light": "a person with light skin tone",
        "medium": "a person with medium skin tone",
        "dark": "a person with dark skin tone",
    },
    "clothing_color": {
        "black": "a person wearing black clothing",
        "white": "a person wearing white clothing",
        "red": "a person wearing red clothing",
        "blue": "a person wearing blue clothing",
        "green": "a person wearing green clothing",
        "yellow": "a person wearing yellow clothing",
    },
}


def build_attribute_prompts(attributes: dict) -> list[str]:
    """Build CLIP text prompts from selected facial attributes."""
    prompts: list[str] = []
    for key, value in attributes.items():
        if not value or str(value).lower() in ("all", "any", ""):
            continue
        mapping = ATTRIBUTE_PROMPTS.get(key, {})
        prompt = mapping.get(str(value).lower())
        if prompt:
            prompts.append(prompt)
    if not prompts:
        prompts.append("a person in an aerial drone photograph")
    return prompts


def _encode_clip_text(clip_model, clip_proc, device, texts: list[str]):
    import torch

    with torch.no_grad():
        inputs = clip_proc(text=texts, return_tensors="pt", padding=True, truncation=True)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        feats = clip_model.get_text_features(**inputs)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats


def _encode_clip_image(clip_model, clip_proc, device, pil_img: PILImage.Image):
    import torch

    with torch.no_grad():
        inputs = clip_proc(images=pil_img, return_tensors="pt")
        feat = clip_model.get_image_features(pixel_values=inputs["pixel_values"].to(device))
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat


def _detect_faces_in_person_crop(person_crop: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Return face bboxes (x, y, w, h) inside a person crop."""
    if person_crop is None or person_crop.size == 0:
        return []
    gray = cv2.cvtColor(person_crop, cv2.COLOR_BGR2GRAY)
    faces = _FACE_CASCADE.detectMultiScale(
        gray, scaleFactor=1.08, minNeighbors=4, minSize=(24, 24)
    )
    if len(faces) > 0:
        return [tuple(map(int, f)) for f in faces]
    # Fallback: upper 40% of person bbox often contains the face from aerial view
    h, w = person_crop.shape[:2]
    return [(int(w * 0.15), 0, int(w * 0.7), int(h * 0.42))]


def _crop_face_from_person(frame: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> Optional[np.ndarray]:
    h, w = frame.shape[:2]
    px1, py1 = max(0, x1), max(0, y1)
    px2, py2 = min(w, x2), min(h, y2)
    person = frame[py1:py2, px1:px2]
    if person.size == 0:
        return None

    faces = _detect_faces_in_person_crop(person)
    if not faces:
        return None

    # Use largest detected face
    fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    face = person[fy : fy + fh, fx : fx + fw]
    if face.size == 0 or face.shape[0] < 20 or face.shape[1] < 20:
        return None
    return face


def scan_video_facial_attributes(
    video_path: str,
    attributes: dict,
    target_image_bytes: Optional[bytes] = None,
    frame_interval: int = 15,
    similarity_threshold: float = 0.24,
    target_weight: float = 0.55,
) -> dict:
    """
    Scan video for persons matching facial attributes.
    Uses YOLO person detection + Haar face crop + CLIP attribute scoring.
    """
    import torch
    from transformers import CLIPModel, CLIPProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"
    clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    clip_proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    attr_prompts = build_attribute_prompts(attributes)
    text_feats = _encode_clip_text(clip_model, clip_proc, device, attr_prompts)

    target_feat = None
    if target_image_bytes:
        target_pil = PILImage.open(__import__("io").BytesIO(target_image_bytes)).convert("RGB")
        target_feat = _encode_clip_image(clip_model, clip_proc, device, target_pil)

    # Person detector — prefer VisDrone fine-tuned model
    model_path = "skyrecon_visdrone.pt" if os.path.exists("skyrecon_visdrone.pt") else settings.YOLO_MODEL
    yolo = _get_model(model_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Cannot open video source")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    matches: list[dict] = []
    seen_tracks: set[int] = set()
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval != 0:
            frame_idx += 1
            continue

        timestamp = frame_idx / fps
        fh, fw = frame.shape[:2]

        results = yolo.track(
            frame,
            persist=True,
            verbose=False,
            conf=0.30,
            tracker="bytetrack.yaml",
        )

        PERSON_NAMES = {"person", "pedestrian", "people"}

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0])
                names = yolo.names
                cls_name = (names[cls_id] if isinstance(names, (list, tuple)) else names.get(cls_id, "")).lower()
                if cls_name not in PERSON_NAMES:
                    continue

                track_id = int(box.id[0]) if box.id is not None else None
                if track_id is not None and track_id in seen_tracks:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                face_crop = _crop_face_from_person(frame, x1, y1, x2, y2)
                if face_crop is None:
                    # Wider upper-body fallback for aerial angles where Haar misses
                    upper_h = max(40, int((y2 - y1) * 0.45))
                    face_crop = frame[max(0, y1) : min(fh, y1 + upper_h), max(0, x1) : min(fw, x2)]
                    if face_crop.size == 0:
                        continue

                face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                face_pil = PILImage.fromarray(face_rgb)
                face_feat = _encode_clip_image(clip_model, clip_proc, device, face_pil)

                attr_score = float((face_feat @ text_feats.T).mean().item())

                ref_score = 0.0
                if target_feat is not None:
                    ref_score = float((face_feat @ target_feat.T).squeeze().item())

                if target_feat is not None:
                    confidence = target_weight * ref_score + (1 - target_weight) * attr_score
                else:
                    confidence = attr_score

                if confidence < similarity_threshold:
                    continue

                if track_id is not None:
                    seen_tracks.add(track_id)

                # Annotated thumbnail
                thumb = frame.copy()
                cv2.rectangle(thumb, (x1, y1), (x2, y2), (57, 255, 20), 2)
                cv2.putText(
                    thumb,
                    f"Match {confidence:.0%}",
                    (x1, max(y1 - 8, 16)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (57, 255, 20),
                    2,
                )
                _, buf = cv2.imencode(".jpg", thumb, [cv2.IMWRITE_JPEG_QUALITY, 72])
                thumb_b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode()

                attr_summary = ", ".join(
                    f"{k}={v}" for k, v in attributes.items()
                    if v and str(v).lower() not in ("all", "any", "")
                )
                matches.append({
                    "timestamp": round(timestamp, 2),
                    "confidence": round(confidence, 3),
                    "attr_score": round(attr_score, 3),
                    "ref_score": round(ref_score, 3) if target_feat is not None else None,
                    "track_id": track_id,
                    "description": (
                        f"Facial match at {int(timestamp // 60):02d}:{int(timestamp % 60):02d} "
                        f"— {confidence:.0%} ({attr_summary or 'attributes matched'})"
                    ),
                    "thumbnail": thumb_b64,
                    "attributes_matched": attributes,
                })

        frame_idx += 1

    cap.release()
    matches.sort(key=lambda x: x["confidence"], reverse=True)
    return {
        "matches": matches,
        "total_scanned": frame_idx,
        "threshold": similarity_threshold,
        "search_mode": "facial_attributes",
        "attribute_prompts": attr_prompts,
    }
