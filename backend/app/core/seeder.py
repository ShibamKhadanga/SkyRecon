from sqlalchemy import text
from sqlalchemy.orm import Session
from ..models.models import Analysis, Category
import random
from datetime import datetime, timedelta

def seed_mock_data_if_empty(db: Session):
    """
    Seeds mock analyses, detections, disaster events, and reports 
    using the installed PostgreSQL PL/pgSQL stored procedures
    if no analyses exist yet.
    """
    # Check if we already have analyses
    if db.query(Analysis).count() > 0:
        print("Database already has analyses. Skipping mock seeding.")
        return

    print("[SEEDER] Database is empty. Seeding mock data using PL/pgSQL stored procedures...")

    # Get a map of category name to id
    categories = db.query(Category).all()
    category_map = {cat.name: cat.id for cat in categories}
    
    if not category_map:
        print("[SEEDER] Warning: No categories found to seed detections. Make sure seed_default_categories ran.")
        return

    # ── 1. Seed Analysis Jobs ──
    mock_jobs = [
        {
            "project_name": "Highway Survey - NH48",
            "description": "Routine aerial survey of national highway NH48 for pothole detection and traffic monitoring.",
            "location": "Gurugram, Haryana",
            "drone_model": "DJI Matrice 300 RTK",
            "detection_mode": "standard",
            "custom_query": "",
            "date_offset": 0
        },
        {
            "project_name": "Industrial Zone Fire Safety Scan",
            "description": "Thermal and visual scanning of the Western Industrial Sector for fire hazard detection.",
            "location": "Noida, Uttar Pradesh",
            "drone_model": "DJI Mavic 3 Thermal",
            "detection_mode": "custom",
            "custom_query": "fire, smoke, heat exhaust, chemical container",
            "date_offset": 1
        },
        {
            "project_name": "Park Vegetation Health SCAN",
            "description": "Multispectral canopy analysis to estimate vegetation index and locate dry shrubs.",
            "location": "New Delhi, Delhi",
            "drone_model": "Parrot Bluegrass Fields",
            "detection_mode": "standard",
            "custom_query": "",
            "date_offset": 2
        },
        {
            "project_name": "Kashmir Flood Rescue Operation",
            "description": "Active disaster monitoring and rescue coordination support during recent localized flooding.",
            "location": "Srinagar, Jammu and Kashmir",
            "drone_model": "Custom Octocopter Long-Range",
            "detection_mode": "standard",
            "custom_query": "",
            "date_offset": 3
        }
    ]

    for job in mock_jobs:
        # Call stored procedure 'create_analysis_job'
        result = db.execute(
            text("""
                SELECT create_analysis_job(
                    :project_name, :description, :location, :drone_model, :detection_mode, :custom_query
                )
            """),
            {
                "project_name": job["project_name"],
                "description": job["description"],
                "location": job["location"],
                "drone_model": job["drone_model"],
                "detection_mode": job["detection_mode"],
                "custom_query": job["custom_query"]
            }
        )
        analysis_id = result.scalar()
        
        # Adjust created_at date for realistic history
        db_analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if db_analysis:
            db_analysis.created_at = datetime.utcnow() - timedelta(days=job["date_offset"])
            db.commit()

        print(f"Created Analysis '{job['project_name']}' with ID {analysis_id}")

        # ── 2. Seed Detections ──
        if "Highway" in job["project_name"]:
            # Seed highway traffic & pothole detections
            detections = [
                ("Vehicles", "SUV", 0.94, 28.6139, 77.2090),
                ("Vehicles", "Sedan", 0.88, 28.6142, 77.2093),
                ("Vehicles", "Heavy Truck", 0.91, 28.6135, 77.2085),
                ("Road Potholes", "Pothole Large", 0.85, 28.6150, 77.2100),
                ("Road Potholes", "Pothole Medium", 0.79, 28.6148, 77.2098),
                ("Street Lights", "LED Street Light", 0.95, 28.6130, 77.2080)
            ]
        elif "Fire" in job["project_name"]:
            # Seed fire/smoke detections
            detections = [
                ("Fire & Smoke", "Active Fire Flare", 0.98, 28.6200, 77.2150),
                ("Fire & Smoke", "Thick Black Smoke", 0.94, 28.6205, 77.2155),
                ("Buildings", "Industrial Warehouse", 0.90, 28.6195, 77.2145),
                ("People", "Security Guard", 0.82, 28.6210, 77.2160)
            ]
        elif "Park" in job["project_name"]:
            # Seed vegetation & green areas
            detections = [
                ("Trees", "Banyan Tree", 0.92, 28.6300, 77.1950),
                ("Trees", "Neem Tree", 0.89, 28.6295, 77.1945),
                ("Water Bodies", "Central Park Pond", 0.96, 28.6310, 77.1960),
                ("People", "Jogger", 0.87, 28.6305, 77.1955)
            ]
        else:
            # Seed flood rescue detections
            detections = [
                ("Flood Water", "Submerged Road", 0.99, 28.6050, 77.2000),
                ("People", "Stranded Citizen", 0.95, 28.6055, 77.2005),
                ("People", "Rescue Worker", 0.92, 28.6048, 77.1998),
                ("Houses", "Submerged House Ground Floor", 0.88, 28.6060, 77.2010)
            ]

        # Call record_detection stored procedure for each
        total_objects = 0
        for cat_name, label, conf, lat, lon in detections:
            cat_id = category_map.get(cat_name)
            if not cat_id:
                continue
                
            db.execute(
                text("""
                    SELECT record_detection(
                        :analysis_id, :category_id, :label, :confidence,
                        :bbox_x, :bbox_y, :bbox_w, :bbox_h,
                        :frame_number, :timestamp, :gps_lat, :gps_lon, :characteristics
                    )
                """),
                {
                    "analysis_id": analysis_id,
                    "category_id": cat_id,
                    "label": label,
                    "confidence": conf,
                    "bbox_x": random.uniform(100, 1000),
                    "bbox_y": random.uniform(100, 800),
                    "bbox_w": random.uniform(50, 200),
                    "bbox_h": random.uniform(50, 200),
                    "frame_number": random.randint(1, 500),
                    "timestamp": random.uniform(0.5, 45.0),
                    "gps_lat": lat,
                    "gps_lon": lon,
                    "characteristics": '{"speed_kph": 45, "direction": "North"}' if cat_name == "Vehicles" else '{}'
                }
            )
            total_objects += 1

        # Complete the analysis job using complete_analysis stored procedure
        db.execute(
            text("SELECT complete_analysis(:analysis_id, :total_objects, :processing_time)"),
            {
                "analysis_id": analysis_id,
                "total_objects": total_objects,
                "processing_time": random.uniform(12.4, 38.6)
            }
        )
        db.commit()

        # ── 3. Seed Disaster Events if applicable ──
        if "Fire" in job["project_name"]:
            db.execute(
                text("""
                    SELECT record_disaster_event(
                        :analysis_id, :disaster_type, :severity, :confidence,
                        :affected_area, :gps_lat, :gps_lon, :timestamp, :frame_number, :recommendations
                    )
                """),
                {
                    "analysis_id": analysis_id,
                    "disaster_type": "fire",
                    "severity": 4,
                    "confidence": 0.98,
                    "affected_area": 250.0,
                    "gps_lat": 28.6200,
                    "gps_lon": 77.2150,
                    "timestamp": 12.5,
                    "frame_number": 375,
                    "recommendations": "Deploy industrial foam trucks. Evacuate 500m downwind buffer zone immediately."
                }
            )
            db.commit()
        elif "Flood" in job["project_name"]:
            db.execute(
                text("""
                    SELECT record_disaster_event(
                        :analysis_id, :disaster_type, :severity, :confidence,
                        :affected_area, :gps_lat, :gps_lon, :timestamp, :frame_number, :recommendations
                    )
                """),
                {
                    "analysis_id": analysis_id,
                    "disaster_type": "flood",
                    "severity": 5,
                    "confidence": 0.99,
                    "affected_area": 1200.0,
                    "gps_lat": 28.6050,
                    "gps_lon": 77.2000,
                    "timestamp": 4.2,
                    "frame_number": 126,
                    "recommendations": "Deploy emergency motorboats. Establish aerial drone supply dropping coordinates."
                }
            )
            db.commit()

        # ── 4. Seed Reports ──
        # Generate report record using stored procedure
        report_title = f"AI Mapping Intelligence Report - {job['project_name']}"
        report_res = db.execute(
            text("SELECT generate_report_record(:analysis_id, :title, :report_type, :format)"),
            {
                "analysis_id": analysis_id,
                "title": report_title,
                "report_type": "disaster" if ("Fire" in job["project_name"] or "Flood" in job["project_name"]) else "mapping",
                "format": "pdf"
            }
        )
        report_id = report_res.scalar()

        # Mark report as ready using stored procedure
        mock_file_path = f"/reports/report_{analysis_id}.pdf"
        db.execute(
            text("SELECT mark_report_ready(:report_id, :file_path)"),
            {
                "report_id": report_id,
                "file_path": mock_file_path
            }
        )
        db.commit()

    print("[SEEDER] Mock data successfully seeded into PostgreSQL using stored procedures.")
