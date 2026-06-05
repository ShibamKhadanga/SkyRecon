FROM python:3.11-slim

WORKDIR /app

# System dependencies for OpenCV (headless) and libGL
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Download all model weights from GitHub Releases
# This runs once at build time — cached in the image layer
RUN python download_models.py

# HuggingFace Spaces uses port 7860
EXPOSE 7860

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
