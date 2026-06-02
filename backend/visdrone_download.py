"""
VisDrone Dataset Downloader
Uses Ultralytics built-in downloader — handles auth, mirrors, and extraction automatically.
Run: python visdrone_download.py
"""

from ultralytics.utils.downloads import download
from pathlib import Path
import os

SAVE_DIR = Path("visdrone_dataset")
SAVE_DIR.mkdir(exist_ok=True)

# Ultralytics-hosted VisDrone mirrors (same ones used by `yolo train data=VisDrone.yaml`)
URLS = [
    "https://github.com/ultralytics/assets/releases/download/v0.0.0/VisDrone2019-DET-train.zip",
    "https://github.com/ultralytics/assets/releases/download/v0.0.0/VisDrone2019-DET-val.zip",
]

print("Downloading VisDrone2019-DET train + val via Ultralytics downloader...")
print("This may take 20-30 minutes depending on your internet speed (~8GB total)\n")

for url in URLS:
    print(f"→ {url.split('/')[-1]}")
    download(url, dir=SAVE_DIR, unzip=True, delete=True, threads=1)

print(f"\nDataset ready at: {SAVE_DIR.resolve()}")
print("Next step: python visdrone_convert.py")
