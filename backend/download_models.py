"""
SkyRecon — Model Weight Downloader
Downloads all custom-trained .pt model weights from GitHub Releases.
Run automatically during deployment (Render build command / HuggingFace Dockerfile).
"""

import os
import sys
import urllib.request

# GitHub Releases URL — update tag if you create a new release
BASE_URL = "https://github.com/ShibamKhadanga/SkyRecon/releases/download/v1.0-models"

# All models needed by SkyRecon's AI pipeline
# Sizes updated after stripping optimizer state + FP16 conversion
MODELS = [
    ("skyrecon_visdrone.pt",    136),   # Fine-tuned: aerial people + vehicles
    ("skyrecon_rdd2022.pt",      22),   # Fine-tuned: road damage + potholes
    ("skyrecon_fire_smoke.pt",  136),   # Fine-tuned: fire & smoke (optimized — was 521MB)
    ("skyrecon_flood.pt",       136),   # Fine-tuned: flood water
    ("skyrecon_trees_plants.pt", 22),   # Fine-tuned: trees & vegetation (optimized — was 86MB)
    ("yolov8s.pt",               22),   # COCO general fallback (balanced)
    ("yolov8x.pt",              136),   # Full accuracy base model
]

# Maximum allowed file size (MB). If a downloaded model is larger, it probably
# contains optimizer state and will degrade inference quality.
MAX_MODEL_SIZE_MB = 200


def _progress_hook(block_num, block_size, total_size):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded / total_size * 100, 100)
        mb = downloaded / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        sys.stdout.write(f"\r  {mb:.1f} / {total_mb:.1f} MB ({pct:.0f}%)")
        sys.stdout.flush()


def download_models():
    print("=" * 60)
    print("SkyRecon — Downloading AI Model Weights")
    print("=" * 60)

    for model_name, approx_mb in MODELS:
        if os.path.exists(model_name):
            size_mb = os.path.getsize(model_name) / (1024 * 1024)
            # Validate existing model isn't bloated
            if size_mb > MAX_MODEL_SIZE_MB:
                print(f"[WARN] {model_name} is {size_mb:.0f} MB (max {MAX_MODEL_SIZE_MB} MB)")
                print(f"       Run: python optimize_models.py {model_name}")
            else:
                print(f"[SKIP] {model_name} already exists ({size_mb:.0f} MB)")
            continue

        url = f"{BASE_URL}/{model_name}"
        print(f"\n[DOWN] {model_name} (~{approx_mb} MB)")
        print(f"       {url}")

        try:
            urllib.request.urlretrieve(url, model_name, reporthook=_progress_hook)
            # Validate downloaded size
            actual_mb = os.path.getsize(model_name) / (1024 * 1024)
            if actual_mb > MAX_MODEL_SIZE_MB:
                print(f"\n[WARN] {model_name} is {actual_mb:.0f} MB — may contain optimizer state")
                print(f"       Run: python optimize_models.py {model_name}")
            else:
                print(f"\n[OK]   {model_name} downloaded successfully ({actual_mb:.0f} MB)")
        except Exception as e:
            print(f"\n[ERR]  Failed to download {model_name}: {e}")
            print(f"       Upload it manually to GitHub Releases → v1.0-models")

    print("\n" + "=" * 60)
    print("All models ready.")
    print("=" * 60)


if __name__ == "__main__":
    download_models()

