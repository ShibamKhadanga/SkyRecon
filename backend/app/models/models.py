from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    color = Column(String(20), default="#22c55e")
    icon = Column(String(50), default="tag")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    characteristics = relationship("Characteristic", back_populates="category", cascade="all, delete-orphan")
    detections = relationship("Detection", back_populates="category")


class Characteristic(Base):
    __tablename__ = "characteristics"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    active = Column(Boolean, default=True)
    
    category = relationship("Category", back_populates="characteristics")


class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(200))
    description = Column(Text)
    video_path = Column(String(500))
    location = Column(String(200))
    drone_model = Column(String(100))
    detection_mode = Column(String(50), default="standard")  # standard, custom, nlq
    custom_query = Column(Text)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    total_objects = Column(Integer, default=0)
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    detections = relationship("Detection", back_populates="analysis", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="analysis")


class Detection(Base):
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    label = Column(String(200))
    confidence = Column(Float)
    bbox_x = Column(Float)
    bbox_y = Column(Float)
    bbox_w = Column(Float)
    bbox_h = Column(Float)
    frame_number = Column(Integer)
    timestamp = Column(Float)  # seconds in video
    gps_lat = Column(Float)
    gps_lon = Column(Float)
    characteristics = Column(JSON)  # store detected characteristics
    screenshot_path = Column(String(500))
    
    analysis = relationship("Analysis", back_populates="detections")
    category = relationship("Category", back_populates="detections")


class DisasterEvent(Base):
    __tablename__ = "disaster_events"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"))
    disaster_type = Column(String(100))  # flood, fire, structural, cyclone, landslide
    severity = Column(Integer, default=1)  # 1-5
    confidence = Column(Float)
    affected_area = Column(Float)  # sq meters
    gps_lat = Column(Float)
    gps_lon = Column(Float)
    timestamp = Column(Float)
    frame_number = Column(Integer)
    screenshot_path = Column(String(500))
    recommendations = Column(Text)
    resource_estimation = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"))
    title = Column(String(300))
    report_type = Column(String(50))  # mapping, disaster
    format = Column(String(10), default="pdf")  # pdf, docx, excel
    file_path = Column(String(500))
    status = Column(String(50), default="generating")  # generating, ready, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    analysis = relationship("Analysis", back_populates="reports")
