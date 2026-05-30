from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import httpx
from ...database import get_db
from ...schemas import DashboardStats
from ...models.models import Detection, Category, DisasterEvent

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Returns actual platform statistics using get_dashboard_stats() PL/pgSQL function."""
    try:
        result = db.execute(text("SELECT * FROM get_dashboard_stats()")).first()
        if result:
            return DashboardStats(
                total_analyses=result.total_analyses or 0,
                total_detections=result.total_detections or 0,
                total_reports=result.total_reports or 0,
                active_alerts=result.active_alerts or 0,
            )
    except Exception as e:
        print(f"⚠️ Error calling get_dashboard_stats stored procedure: {e}")
    
    # Fallback to zeros if procedure fails
    return DashboardStats(
        total_analyses=0,
        total_detections=0,
        total_reports=0,
        active_alerts=0,
    )


@router.get("/recent-analyses")
def get_recent_analyses(db: Session = Depends(get_db)):
    """Returns the most recent analyses using get_recent_analyses() PL/pgSQL function."""
    try:
        result = db.execute(text("SELECT * FROM get_recent_analyses(5)")).all()
        return [
            {
                "id": r.id,
                "project_name": r.project_name,
                "status": r.status,
                "total_objects": r.total_objects,
                "detection_mode": r.detection_mode,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in result
        ]
    except Exception as e:
        print(f"⚠️ Error calling get_recent_analyses stored procedure: {e}")
        return []


@router.get("/map-markers")
def get_map_markers(db: Session = Depends(get_db)):
    """Returns active map markers dynamically queried from actual DB detections & disaster events."""
    markers = []
    
    # ── 1. Fetch Detections with coordinates ──
    try:
        detections = db.query(
            Detection.id,
            Detection.gps_lat,
            Detection.gps_lon,
            Detection.label,
            Detection.confidence,
            Category.name.label("cat_name"),
            Category.color.label("cat_color")
        ).join(Category, Detection.category_id == Category.id).filter(
            Detection.gps_lat.isnot(None),
            Detection.gps_lon.isnot(None)
        ).all()

        for d in detections:
            # Estimate severity from confidence
            severity = 3 if d.confidence > 0.9 else (2 if d.confidence > 0.8 else 1)
            markers.append({
                "id": f"det-{d.id}",
                "lat": d.gps_lat,
                "lon": d.gps_lon,
                "label": f"{d.cat_name}: {d.label}",
                "type": d.cat_name.lower(),
                "color": d.cat_color,
                "severity": severity,
                "detections": 1
            })
    except Exception as e:
        print(f"⚠️ Error querying map-marker detections: {e}")

    # ── 2. Fetch Disaster Events with coordinates ──
    try:
        disasters = db.query(
            DisasterEvent.id,
            DisasterEvent.gps_lat,
            DisasterEvent.gps_lon,
            DisasterEvent.disaster_type,
            DisasterEvent.severity,
            DisasterEvent.confidence
        ).filter(
            DisasterEvent.gps_lat.isnot(None),
            DisasterEvent.gps_lon.isnot(None)
        ).all()

        for d in disasters:
            markers.append({
                "id": f"dis-{d.id}",
                "lat": d.gps_lat,
                "lon": d.gps_lon,
                "label": f"🚨 Disaster: {d.disaster_type.upper()}",
                "type": "disaster",
                "color": "#ef4444",  # High-contrast disaster red
                "severity": d.severity,
                "detections": 5
            })
    except Exception as e:
        print(f"⚠️ Error querying map-marker disasters: {e}")

    return markers


@router.get("/live-aircraft")
async def get_live_aircraft(lat: float = 20.5, lon: float = 78.9, radius: float = 8.0):
    """
    Proxy for OpenSky Network REST API — free, no API key required for anonymous access.
    Returns aircraft currently in a bounding box around the given lat/lon.
    radius is in degrees (~111km per degree).
    """
    lamin = lat - radius
    lamax = lat + radius
    lomin = lon - radius
    lomax = lon + radius
    url = f"https://opensky-network.org/api/states/all?lamin={lamin}&lomin={lomin}&lamax={lamax}&lomax={lomax}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers={"User-Agent": "SkyRecon/1.0"})
            if resp.status_code != 200:
                return {"aircraft": [], "error": f"OpenSky returned {resp.status_code}"}
            data = resp.json()
            states = data.get("states") or []
            aircraft = []
            for s in states:
                # OpenSky state vector fields:
                # [0]=icao24, [1]=callsign, [2]=origin_country, [5]=lon, [6]=lat,
                # [7]=baro_altitude, [9]=velocity, [10]=heading, [13]=on_ground
                if s[6] is None or s[5] is None:
                    continue
                aircraft.append({
                    "icao": s[0],
                    "callsign": (s[1] or "").strip() or s[0],
                    "country": s[2],
                    "lat": s[6],
                    "lon": s[5],
                    "altitude": round(s[7]) if s[7] else 0,       # metres
                    "speed": round(s[9]) if s[9] else 0,           # m/s
                    "heading": round(s[10]) if s[10] else 0,
                    "on_ground": s[8] if len(s) > 8 else False,
                })
            return {"aircraft": aircraft, "count": len(aircraft)}
    except Exception as e:
        return {"aircraft": [], "error": str(e)}


@router.get("/live-satellites")
async def get_live_satellites():
    """
    Fetches active satellite TLE data from Celestrak (free, no API key).
    Returns the 50 brightest / most visible satellites with computed current positions
    using a simplified SGP4-like propagation (mean motion approximation).
    """
    import math, time

    url = "https://celestrak.org/SOCRATES/query.php?CODE=ALL&MAX=50&TYPE=json"
    # Fallback: use the visual satellites group which is always available
    tle_url = "https://celestrak.org/SOCRATES/query.php?CODE=ALL&MAX=50&TYPE=json"
    # Use the simpler catalog endpoint instead
    catalog_url = "https://celestrak.org/pub/TLE/catalog.txt"

    # Use the 'visual' group — brightest satellites visible to naked eye
    visual_url = "https://celestrak.org/SOCRATES/query.php?CODE=ALL&MAX=50&TYPE=json"
    tle_text_url = "https://celestrak.org/pub/TLE/visual.txt"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(tle_text_url, headers={"User-Agent": "SkyRecon/1.0"})
            if resp.status_code != 200:
                return {"satellites": [], "error": f"Celestrak returned {resp.status_code}"}

            lines = [l.strip() for l in resp.text.splitlines() if l.strip()]
            satellites = []
            now = time.time()  # Unix timestamp

            i = 0
            while i + 2 < len(lines):
                name = lines[i]
                tle1 = lines[i + 1]
                tle2 = lines[i + 2]
                i += 3

                if not tle1.startswith("1 ") or not tle2.startswith("2 "):
                    i -= 2
                    continue

                try:
                    # Parse mean motion (rev/day) and inclination from TLE line 2
                    inc = float(tle2[8:16])          # inclination degrees
                    mean_motion = float(tle2[52:63]) # rev/day
                    mean_anomaly = float(tle2[43:51])# degrees at epoch

                    # Parse epoch from TLE line 1
                    epoch_str = tle1[18:32].strip()
                    epoch_year = int(epoch_str[:2])
                    epoch_year += 2000 if epoch_year < 57 else 1900
                    epoch_day = float(epoch_str[2:])
                    import datetime
                    epoch_dt = datetime.datetime(epoch_year, 1, 1) + datetime.timedelta(days=epoch_day - 1)
                    epoch_ts = epoch_dt.timestamp()

                    # Minutes since epoch
                    dt_min = (now - epoch_ts) / 60.0
                    # Current mean anomaly (degrees)
                    n_deg_per_min = mean_motion * 360.0 / 1440.0
                    ma = (mean_anomaly + n_deg_per_min * dt_min) % 360.0

                    # Approximate lat/lon from inclination + mean anomaly
                    # This is a rough approximation — good enough for map display
                    lat_sat = inc * math.sin(math.radians(ma))
                    lon_sat = (ma * 2 - 180 + (dt_min * 0.25)) % 360 - 180

                    # Orbital period minutes
                    period_min = 1440.0 / mean_motion
                    altitude_km = round(((period_min / 84.0) ** (2/3)) * 6371 - 6371)

                    satellites.append({
                        "name": name,
                        "lat": round(lat_sat, 3),
                        "lon": round(lon_sat, 3),
                        "altitude_km": max(200, min(altitude_km, 36000)),
                        "inclination": round(inc, 1),
                        "period_min": round(period_min, 1),
                    })

                    if len(satellites) >= 50:
                        break
                except Exception:
                    continue

            return {"satellites": satellites, "count": len(satellites)}

    except Exception as e:
        return {"satellites": [], "error": str(e)}
