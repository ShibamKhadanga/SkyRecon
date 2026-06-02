"""
VisDrone → YOLO Format Converter
Converts VisDrone annotation format to YOLO txt format.

VisDrone classes (0-indexed):
  0=pedestrian, 1=people, 2=bicycle, 3=car, 4=van,
  5=truck, 6=tricycle, 7=awning-tricycle, 8=bus, 9=motor

We map these to SkyRecon-relevant YOLO classes:
  pedestrian + people → person (COCO class 0)
  bicycle             → bicycle (COCO class 1)
  car + van           → car (COCO class 2)
  truck               → truck (COCO class 3)
  bus                 → bus (COCO class 4)
  motor               → motorcycle (COCO class 5)
  tricycle + awning   → motorcycle (COCO class 5)  ← closest match

Run: python visdrone_convert.py
"""

import os
import shutil
from pathlib import Path

VISDRONE_DIR = "visdrone_dataset"
YOLO_DIR     = "visdrone_yolo"

# VisDrone class id → YOLO class id (COCO-aligned)
# VisDrone: 0=pedestrian,1=people,2=bicycle,3=car,4=van,5=truck,6=tricycle,7=awning-tricycle,8=bus,9=motor
# We skip class 0 (ignored regions) in VisDrone — those have class_id=0 in annotations
# VisDrone annotation format: <bbox_left>,<bbox_top>,<bbox_width>,<bbox_height>,<score>,<category>,<truncation>,<occlusion>
# category is 1-indexed in the annotation file

VISDRONE_TO_YOLO = {
    1: 0,   # pedestrian → person
    2: 0,   # people     → person
    3: 1,   # bicycle    → bicycle
    4: 2,   # car        → car
    5: 2,   # van        → car
    6: 7,   # truck      → truck
    7: 5,   # tricycle   → motorcycle
    8: 5,   # awning-tricycle → motorcycle
    9: 5,   # bus        → bus  (mapped to 5 to keep 6-class output)
    10: 3,  # motor      → motorcycle
}

# Final YOLO class names for the dataset YAML
YOLO_CLASSES = ["person", "bicycle", "car", "motorcycle", "bus", "truck"]

SPLITS = {
    "train": f"{VISDRONE_DIR}/VisDrone2019-DET-train",
    "val":   f"{VISDRONE_DIR}/VisDrone2019-DET-val",
}


def convert_annotation(ann_path: Path, img_w: int, img_h: int) -> list[str]:
    lines = []
    for raw in ann_path.read_text().strip().splitlines():
        parts = raw.strip().split(",")
        if len(parts) < 6:
            continue
        x, y, w, h = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        cat = int(parts[5])
        if cat == 0 or cat not in VISDRONE_TO_YOLO:
            continue  # skip ignored regions and unmapped classes
        if w <= 0 or h <= 0:
            continue
        yolo_cls = VISDRONE_TO_YOLO[cat]
        # Convert to YOLO normalized xywh (center)
        cx = (x + w / 2) / img_w
        cy = (y + h / 2) / img_h
        nw = w / img_w
        nh = h / img_h
        lines.append(f"{yolo_cls} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
    return lines


def convert_split(split_name: str, split_dir: str):
    img_dir = Path(split_dir) / "images"
    ann_dir = Path(split_dir) / "annotations"

    out_img = Path(YOLO_DIR) / split_name / "images"
    out_lbl = Path(YOLO_DIR) / split_name / "labels"
    out_img.mkdir(parents=True, exist_ok=True)
    out_lbl.mkdir(parents=True, exist_ok=True)

    images = sorted(img_dir.glob("*.jpg")) + sorted(img_dir.glob("*.png"))
    print(f"Converting {split_name}: {len(images)} images ...")

    for img_path in images:
        ann_path = ann_dir / (img_path.stem + ".txt")
        if not ann_path.exists():
            continue

        # Get image dimensions using cv2
        import cv2
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        img_h, img_w = img.shape[:2]

        yolo_lines = convert_annotation(ann_path, img_w, img_h)
        if not yolo_lines:
            continue

        shutil.copy2(img_path, out_img / img_path.name)
        (out_lbl / (img_path.stem + ".txt")).write_text("\n".join(yolo_lines))

    print(f"  Done: {split_name}")


for split_name, split_dir in SPLITS.items():
    if not os.path.exists(split_dir):
        print(f"WARNING: {split_dir} not found — run visdrone_download.py first")
        continue
    convert_split(split_name, split_dir)

# Write dataset YAML
yaml_content = f"""# VisDrone fine-tuning dataset for SkyRecon
path: {os.path.abspath(YOLO_DIR)}
train: train/images
val:   val/images

nc: {len(YOLO_CLASSES)}
names: {YOLO_CLASSES}
"""
yaml_path = os.path.join(YOLO_DIR, "visdrone.yaml")
Path(yaml_path).write_text(yaml_content)
print(f"\nDataset YAML written: {yaml_path}")
print("Next step: python visdrone_train.py")
