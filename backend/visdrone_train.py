"""
VisDrone Fine-Tuning Script
Fine-tunes yolov8x.pt on VisDrone aerial dataset.

Expected improvement:
  People detection:   ~75% → ~90% mAP50
  Vehicles (aerial):  ~80% → ~92% mAP50

Run: python visdrone_train.py
GPU:  ~2 hours  |  CPU: ~12 hours (leave overnight)
"""

import os
from pathlib import Path
from ultralytics import YOLO

DATASET_YAML  = "visdrone_yolo/visdrone.yaml"
BASE_MODEL    = "yolov8x.pt"          # downloads automatically if not present
OUTPUT_NAME   = "skyrecon_visdrone"   # saved to runs/detect/skyrecon_visdrone/

if not Path(DATASET_YAML).exists():
    raise FileNotFoundError(
        f"{DATASET_YAML} not found — run visdrone_convert.py first"
    )

model = YOLO(BASE_MODEL)

results = model.train(
    data=DATASET_YAML,
    epochs=10,           # 10 epochs on CPU is realistic (was 50 — too long without GPU)
    imgsz=416,           # Reduced from 640 — faster on CPU, still good for aerial
    batch=4,             # Reduced from 8 — safer for CPU RAM
    workers=2,
    device="0" if os.environ.get("CUDA_VISIBLE_DEVICES") else "cpu",
    project="runs/detect",
    name=OUTPUT_NAME,
    exist_ok=True,
    patience=5,          # Early stop after 5 epochs no improvement
    save=True,
    save_period=5,
    val=True,
    degrees=15.0,
    translate=0.1,
    scale=0.5,
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.0,           # Disabled — saves time on CPU
    freeze=10,
    lr0=0.001,
    lrf=0.01,
    warmup_epochs=1,     # Reduced from 3
    cos_lr=True,
    label_smoothing=0.1,
    verbose=True,
)

# Best model path
best = Path(f"runs/detect/{OUTPUT_NAME}/weights/best.pt")
print(f"\n{'='*60}")
print(f"Training complete!")
print(f"Best model: {best.resolve()}")
print(f"\nTo use in SkyRecon, copy the model and update .env:")
print(f"  copy {best} SkyRecon\\backend\\skyrecon_visdrone.pt")
print(f"  Then set in .env:  YOLO_MODEL=skyrecon_visdrone.pt")
print(f"{'='*60}")
