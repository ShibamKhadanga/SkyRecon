from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    APP_NAME: str = "SkyRecon"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── PostgreSQL Database ──
    # Connection parameters (override via .env file)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "skyrecon"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"

    # Constructed URL (SQLAlchemy format)
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
    YOLO_MODEL: str = "yolov8n.pt"
    CONFIDENCE_THRESHOLD: float = 0.5

    # CORS
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure required directories exist
for d in [settings.UPLOAD_DIR, settings.REPORTS_DIR, settings.SCREENSHOTS_DIR]:
    Path(d).mkdir(parents=True, exist_ok=True)
