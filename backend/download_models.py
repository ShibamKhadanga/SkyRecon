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
MODELS = [
    ("skyrecon_visdrone.pt",    136),   # Fine-tuned: aerial people + vehicles
    ("skyrecon_rdd2022.pt",      22),   # Fine-tuned: road damage + potholes
    ("skyrecon_fire_smoke.pt",  545),   # Fine-tuned: fire & smoke
    ("skyrecon_flood.pt",       136),   # Fine-tuned: flood water
    ("skyrecon_trees_plants.pt", 89),   # Fine-tuned: trees & vegetation
    ("yolov8s.pt",               22),   # COCO general fallback (balanced)
    ("yolov8x.pt",              136),  # Full accuracy base model
]


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
            print(f"[SKIP] {model_name} already exists ({size_mb:.0f} MB)")
            continue

        url = f"{BASE_URL}/{model_name}"
        print(f"\n[DOWN] {model_name} (~{approx_mb} MB)")
        print(f"       {url}")

        try:
            urllib.request.urlretrieve(url, model_name, reporthook=_progress_hook)
            print(f"\n[OK]   {model_name} downloaded successfully")
        except Exception as e:
            print(f"\n[ERR]  Failed to download {model_name}: {e}")
            print(f"       Upload it manually to GitHub Releases → v1.0-models")

    print("\n" + "=" * 60)
    print("All models ready.")
    print("=" * 60)


if __name__ == "__main__":
    download_models()
