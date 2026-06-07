"""
SkyRecon — Model Weight Optimizer
Strips optimizer state, EMA weights, and training artifacts from .pt checkpoints.

The skyrecon_fire_smoke.pt is 521 MB — a properly exported YOLOv8x should be ~130 MB.
The extra 390 MB is optimizer state (Adam/SGD moments) that:
  1. Wastes disk space and download bandwidth
  2. Can degrade inference accuracy on some PyTorch versions
  3. Slows model loading

Usage:
    python optimize_models.py                     # optimize all .pt in current dir
    python optimize_models.py skyrecon_fire_smoke.pt  # optimize specific model
"""

import os
import sys
import torch


def optimize_model(path: str) -> str:
    """
    Strips optimizer state from a YOLOv8 checkpoint.
    Saves optimized version as {name}_optimized.pt and reports size reduction.
    """
    if not os.path.exists(path):
        print(f"[SKIP] {path} not found")
        return path

    original_size = os.path.getsize(path) / (1024 * 1024)
    print(f"\n[LOAD] {path} ({original_size:.1f} MB)")

    try:
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as e:
        print(f"[ERR]  Cannot load {path}: {e}")
        return path

    # Show what's inside
    if isinstance(ckpt, dict):
        keys = list(ckpt.keys())
        print(f"       Checkpoint keys: {keys}")

        # Remove optimizer state (biggest savings)
        if "optimizer" in ckpt:
            print(f"       Removing optimizer state...")
            ckpt["optimizer"] = None

        # Remove training metadata
        for key in ["updates", "train_args", "train_metrics", "train_results"]:
            if key in ckpt:
                ckpt[key] = None

        # If EMA model exists, promote it to main model (it's usually better)
        if "ema" in ckpt and ckpt["ema"] is not None:
            print(f"       Promoting EMA model to main (EMA = better weights)")
            ckpt["model"] = ckpt["ema"]
            ckpt["ema"] = None

        # Half-precision: convert float32 -> float16 for inference
        if "model" in ckpt and ckpt["model"] is not None:
            model = ckpt["model"]
            if hasattr(model, "half"):
                model.half()
                print(f"       Converted model to FP16")
            if hasattr(model, "state_dict"):
                for k, v in model.state_dict().items():
                    if v.dtype == torch.float32:
                        v.data = v.data.half()

    # Save optimized
    base, ext = os.path.splitext(path)
    out_path = f"{base}_optimized{ext}"
    torch.save(ckpt, out_path)

    new_size = os.path.getsize(out_path) / (1024 * 1024)
    reduction = ((original_size - new_size) / original_size) * 100
    print(f"[SAVE] {out_path} ({new_size:.1f} MB)")
    print(f"       Size reduction: {original_size:.1f} MB → {new_size:.1f} MB ({reduction:.0f}% smaller)")

    return out_path


def main():
    if len(sys.argv) > 1:
        # Optimize specific files
        for path in sys.argv[1:]:
            optimize_model(path)
    else:
        # Optimize all .pt files in current directory
        pt_files = [f for f in os.listdir(".") if f.endswith(".pt") and "optimized" not in f]
        if not pt_files:
            print("[INFO] No .pt files found in current directory")
            return

        print(f"Found {len(pt_files)} model files to optimize:")
        for f in pt_files:
            size = os.path.getsize(f) / (1024 * 1024)
            print(f"  - {f} ({size:.1f} MB)")

        print("\n" + "=" * 60)
        for f in pt_files:
            optimize_model(f)

        print("\n" + "=" * 60)
        print("Done! Optimized files saved with '_optimized' suffix.")
        print("To use: rename optimized file to original name.")
        print("  Example: mv skyrecon_fire_smoke_optimized.pt skyrecon_fire_smoke.pt")


if __name__ == "__main__":
    main()
