from pydantic_settings import BaseSettings
from pydantic import field_validator
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "SkyRecon"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── PostgreSQL Database ──
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "skyrecon"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # File storage
    UPLOAD_DIR: str = "./uploads"
    REPORTS_DIR: str = "./reports"
    SCREENSHOTS_DIR: str = "./screenshots"

    # AI Settings
    YOLO_MODEL: str = "yolov8s.pt"
    CONFIDENCE_THRESHOLD: float = 0.5
    MIN_DISPLAY_CONFIDENCE: float = 0.35  # Post-detection gate (lowered: CLIP dedup handles FPs)

    # CORS — accepts plain string, comma-separated, or JSON array from env
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            # JSON array format: ["url1","url2"]
            if v.startswith("["):
                import json
                return json.loads(v)
            # Comma-separated: url1,url2
            if "," in v:
                return [i.strip() for i in v.split(",")]
            # Single value: * or https://example.com
            return [v]
        return v

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure required directories exist
for d in [settings.UPLOAD_DIR, settings.REPORTS_DIR, settings.SCREENSHOTS_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)