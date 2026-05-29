from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Category Schemas ──
class CharacteristicBase(BaseModel):
    name: str
    active: bool = True

class CharacteristicResponse(CharacteristicBase):
    id: int
    category_id: int
    class Config: from_attributes = True

class CategoryBase(BaseModel):
    name: str
    color: str = "#22c55e"
    icon: str = "tag"
    active: bool = True

class CategoryCreate(CategoryBase):
    characteristics: List[CharacteristicBase] = []

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    active: Optional[bool] = None

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    characteristics: List[CharacteristicResponse] = []
    class Config: from_attributes = True


# ── Analysis Schemas ──
class AnalysisCreate(BaseModel):
    project_name: str
    description: Optional[str] = ""
    location: Optional[str] = ""
    drone_model: Optional[str] = ""
    detection_mode: str = "standard"
    custom_query: Optional[str] = ""
    selected_categories: List[int] = []

class AnalysisResponse(BaseModel):
    id: int
    project_name: str
    description: Optional[str]
    video_path: Optional[str]
    location: Optional[str]
    drone_model: Optional[str]
    detection_mode: str
    status: str
    total_objects: int
    processing_time: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    class Config: from_attributes = True


# ── Detection Schemas ──
class DetectionResponse(BaseModel):
    id: int
    label: str
    confidence: float
    bbox_x: Optional[float]
    bbox_y: Optional[float]
    bbox_w: Optional[float]
    bbox_h: Optional[float]
    frame_number: Optional[int]
    timestamp: Optional[float]
    gps_lat: Optional[float]
    gps_lon: Optional[float]
    characteristics: Optional[dict]
    screenshot_path: Optional[str]
    class Config: from_attributes = True


# ── Disaster Schemas ──
class DisasterEventResponse(BaseModel):
    id: int
    disaster_type: str
    severity: int
    confidence: float
    affected_area: Optional[float]
    gps_lat: Optional[float]
    gps_lon: Optional[float]
    timestamp: Optional[float]
    recommendations: Optional[str]
    resource_estimation: Optional[dict]
    created_at: datetime
    class Config: from_attributes = True


# ── Report Schemas ──
class ReportCreate(BaseModel):
    analysis_id: int
    title: str
    report_type: str = "mapping"
    format: str = "pdf"

class ReportResponse(BaseModel):
    id: int
    analysis_id: int
    title: str
    report_type: str
    format: str
    file_path: Optional[str]
    status: str
    created_at: datetime
    class Config: from_attributes = True


# ── Dashboard Schemas ──
class DashboardStats(BaseModel):
    total_analyses: int
    total_detections: int
    total_reports: int
    active_alerts: int

class RecentAnalysis(BaseModel):
    id: int
    project_name: str
    status: str
    total_objects: int
    created_at: datetime
