from huggingface_hub import hf_hub_download
import shutil

print("Downloading buildings model...")
path = hf_hub_download(
    repo_id="keremberke/yolov8s-building-segmentation",
    filename="best.pt"
)
shutil.copy(path, "skyrecon_buildings.pt")
print("✅ skyrecon_buildings.pt saved!")

print("Downloading solar panels model...")
path2 = hf_hub_download(
    repo_id="finloop/yolov8s-seg-solar-panels",
    filename="best.pt"
)
shutil.copy(path2, "skyrecon_solar_panels.pt")
print("✅ skyrecon_solar_panels.pt saved!")
