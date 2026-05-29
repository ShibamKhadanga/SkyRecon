-- =============================================================
-- SkyRecon  –  PostgreSQL PL/pgSQL Stored Procedures
-- Run once on first boot via database.py → _install_stored_procedures()
-- =============================================================

-- ── 1. upsert_category ────────────────────────────────────────
-- Insert or update a detection category atomically.
CREATE OR REPLACE FUNCTION upsert_category(
    p_name      VARCHAR(100),
    p_color     VARCHAR(20)  DEFAULT '#22c55e',
    p_icon      VARCHAR(50)  DEFAULT 'tag'
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO categories (name, color, icon, active, created_at)
    VALUES (p_name, p_color, p_icon, TRUE, NOW())
    ON CONFLICT (name)
    DO UPDATE SET
        color      = EXCLUDED.color,
        icon       = EXCLUDED.icon,
        active     = TRUE
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;


-- ── 2. create_analysis_job ────────────────────────────────────
-- Registers a new drone video analysis job and returns its ID.
CREATE OR REPLACE FUNCTION create_analysis_job(
    p_project_name   VARCHAR(200),
    p_description    TEXT         DEFAULT '',
    p_location       VARCHAR(200) DEFAULT '',
    p_drone_model    VARCHAR(100) DEFAULT '',
    p_detection_mode VARCHAR(50)  DEFAULT 'standard',
    p_custom_query   TEXT         DEFAULT ''
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO analyses (
        project_name, description, location, drone_model,
        detection_mode, custom_query, status, total_objects, created_at
    )
    VALUES (
        p_project_name, p_description, p_location, p_drone_model,
        p_detection_mode, p_custom_query, 'pending', 0, NOW()
    )
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;


-- ── 3. complete_analysis ──────────────────────────────────────
-- Marks an analysis as completed and updates aggregate counters.
CREATE OR REPLACE FUNCTION complete_analysis(
    p_analysis_id      INTEGER,
    p_total_objects    INTEGER,
    p_processing_time  FLOAT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE analyses
    SET
        status           = 'completed',
        total_objects    = p_total_objects,
        processing_time  = p_processing_time,
        completed_at     = NOW()
    WHERE id = p_analysis_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Analysis % not found', p_analysis_id;
    END IF;
END;
$$;


-- ── 4. record_detection ───────────────────────────────────────
-- Inserts one detection frame result and returns the new row ID.
CREATE OR REPLACE FUNCTION record_detection(
    p_analysis_id   INTEGER,
    p_category_id   INTEGER,
    p_label         VARCHAR(200),
    p_confidence    FLOAT,
    p_bbox_x        FLOAT DEFAULT NULL,
    p_bbox_y        FLOAT DEFAULT NULL,
    p_bbox_w        FLOAT DEFAULT NULL,
    p_bbox_h        FLOAT DEFAULT NULL,
    p_frame_number  INTEGER DEFAULT NULL,
    p_timestamp     FLOAT   DEFAULT NULL,
    p_gps_lat       FLOAT   DEFAULT NULL,
    p_gps_lon       FLOAT   DEFAULT NULL,
    p_characteristics JSONB DEFAULT NULL
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO detections (
        analysis_id, category_id, label, confidence,
        bbox_x, bbox_y, bbox_w, bbox_h,
        frame_number, timestamp, gps_lat, gps_lon,
        characteristics
    )
    VALUES (
        p_analysis_id, p_category_id, p_label, p_confidence,
        p_bbox_x, p_bbox_y, p_bbox_w, p_bbox_h,
        p_frame_number, p_timestamp, p_gps_lat, p_gps_lon,
        p_characteristics
    )
    RETURNING id INTO v_id;

    -- Keep total_objects in sync
    UPDATE analyses
    SET total_objects = total_objects + 1
    WHERE id = p_analysis_id;

    RETURN v_id;
END;
$$;


-- ── 5. record_disaster_event ──────────────────────────────────
-- Inserts a classified disaster event and computes resource estimates.
CREATE OR REPLACE FUNCTION record_disaster_event(
    p_analysis_id    INTEGER,
    p_disaster_type  VARCHAR(100),
    p_severity       INTEGER,
    p_confidence     FLOAT,
    p_affected_area  FLOAT   DEFAULT 0,
    p_gps_lat        FLOAT   DEFAULT NULL,
    p_gps_lon        FLOAT   DEFAULT NULL,
    p_timestamp      FLOAT   DEFAULT NULL,
    p_frame_number   INTEGER DEFAULT NULL,
    p_recommendations TEXT   DEFAULT ''
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_id        INTEGER;
    v_resources JSONB;
    v_teams     INTEGER;
    v_ambulances INTEGER;
    v_boats     INTEGER;
BEGIN
    -- Auto-calculate resource estimation from severity
    v_teams     := GREATEST(1, p_severity * 2);
    v_ambulances := CASE WHEN p_severity >= 4 THEN 3
                         WHEN p_severity >= 3 THEN 2
                         ELSE 1 END;
    v_boats     := CASE WHEN p_disaster_type = 'flood' AND p_severity >= 4 THEN 5
                        WHEN p_disaster_type = 'flood' THEN 2
                        ELSE 0 END;

    v_resources := jsonb_build_object(
        'rescue_teams',        v_teams,
        'ambulances',          v_ambulances,
        'rescue_boats',        v_boats,
        'emergency_vehicles',  CEIL(p_severity::FLOAT / 2),
        'support_staff',       p_severity * 4
    );

    INSERT INTO disaster_events (
        analysis_id, disaster_type, severity, confidence,
        affected_area, gps_lat, gps_lon,
        timestamp, frame_number,
        recommendations, resource_estimation, created_at
    )
    VALUES (
        p_analysis_id, p_disaster_type, p_severity, p_confidence,
        p_affected_area, p_gps_lat, p_gps_lon,
        p_timestamp, p_frame_number,
        p_recommendations, v_resources, NOW()
    )
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;


-- ── 6. get_dashboard_stats ────────────────────────────────────
-- Returns aggregate platform statistics as a single row.
CREATE OR REPLACE FUNCTION get_dashboard_stats()
RETURNS TABLE(
    total_analyses   BIGINT,
    total_detections BIGINT,
    total_reports    BIGINT,
    active_alerts    BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*) FROM analyses)                                      AS total_analyses,
        (SELECT COUNT(*) FROM detections)                                    AS total_detections,
        (SELECT COUNT(*) FROM reports WHERE status = 'ready')               AS total_reports,
        (SELECT COUNT(*) FROM disaster_events WHERE severity >= 4)          AS active_alerts;
END;
$$;


-- ── 7. get_recent_analyses ────────────────────────────────────
-- Returns the N most recently created analysis jobs.
CREATE OR REPLACE FUNCTION get_recent_analyses(p_limit INTEGER DEFAULT 5)
RETURNS TABLE(
    id            INTEGER,
    project_name  VARCHAR,
    status        VARCHAR,
    total_objects INTEGER,
    detection_mode VARCHAR,
    created_at    TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id, a.project_name, a.status,
        a.total_objects, a.detection_mode, a.created_at
    FROM analyses a
    ORDER BY a.created_at DESC
    LIMIT p_limit;
END;
$$;


-- ── 8. generate_report_record ─────────────────────────────────
-- Creates a report row for an analysis and returns its ID.
CREATE OR REPLACE FUNCTION generate_report_record(
    p_analysis_id  INTEGER,
    p_title        VARCHAR(300),
    p_report_type  VARCHAR(50) DEFAULT 'mapping',
    p_format       VARCHAR(10) DEFAULT 'pdf'
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    INSERT INTO reports (analysis_id, title, report_type, format, status, created_at)
    VALUES (p_analysis_id, p_title, p_report_type, p_format, 'generating', NOW())
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$$;


-- ── 9. mark_report_ready ──────────────────────────────────────
-- Marks a report as ready and stores its file path.
CREATE OR REPLACE FUNCTION mark_report_ready(
    p_report_id  INTEGER,
    p_file_path  VARCHAR(500)
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE reports
    SET status    = 'ready',
        file_path = p_file_path
    WHERE id = p_report_id;
END;
$$;


-- ── 10. delete_analysis_cascade ───────────────────────────────
-- Safely deletes an analysis and all related data in correct order.
CREATE OR REPLACE FUNCTION delete_analysis_cascade(p_analysis_id INTEGER)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM reports         WHERE analysis_id = p_analysis_id;
    DELETE FROM disaster_events WHERE analysis_id = p_analysis_id;
    DELETE FROM detections      WHERE analysis_id = p_analysis_id;
    DELETE FROM analyses        WHERE id          = p_analysis_id;
END;
$$;


-- ── 11. search_detections ─────────────────────────────────────
-- Full-text search across detection labels for a given analysis.
CREATE OR REPLACE FUNCTION search_detections(
    p_analysis_id INTEGER,
    p_query       TEXT
)
RETURNS TABLE(
    id            INTEGER,
    label         VARCHAR,
    confidence    FLOAT,
    gps_lat       FLOAT,
    gps_lon       FLOAT,
    "timestamp"   FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT d.id, d.label, d.confidence, d.gps_lat, d.gps_lon, d.timestamp AS "timestamp"
    FROM detections d
    WHERE d.analysis_id = p_analysis_id
      AND d.label ILIKE '%' || p_query || '%'
    ORDER BY d.confidence DESC;
END;
$$;


-- ── 12. seed_default_categories ───────────────────────────────
-- Seeds the 25 master-prompt detection categories (idempotent).
CREATE OR REPLACE FUNCTION seed_default_categories()
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM upsert_category('Vehicles',           '#f97316', 'car');
    PERFORM upsert_category('People',             '#06b6d4', 'user');
    PERFORM upsert_category('Plants',             '#22c55e', 'leaf');
    PERFORM upsert_category('Trees',              '#4ade80', 'tree-pine');
    PERFORM upsert_category('Electric Poles',     '#eab308', 'zap');
    PERFORM upsert_category('Traffic Lights',     '#a855f7', 'traffic-cone');
    PERFORM upsert_category('Roads',              '#64748b', 'road');
    PERFORM upsert_category('Road Potholes',      '#dc2626', 'alert-triangle');
    PERFORM upsert_category('Water Bodies',       '#0ea5e9', 'droplets');
    PERFORM upsert_category('Buildings',          '#8b5cf6', 'building-2');
    PERFORM upsert_category('Houses',             '#c084fc', 'home');
    PERFORM upsert_category('Parking Areas',      '#94a3b8', 'parking-circle');
    PERFORM upsert_category('Garbage Areas',      '#78716c', 'trash-2');
    PERFORM upsert_category('Construction Zones', '#fb923c', 'hard-hat');
    PERFORM upsert_category('Agricultural Land',  '#84cc16', 'wheat');
    PERFORM upsert_category('Animals',            '#d97706', 'paw-print');
    PERFORM upsert_category('Solar Panels',       '#fbbf24', 'sun');
    PERFORM upsert_category('Bridges',            '#6b7280', 'bridge');
    PERFORM upsert_category('Railway Tracks',     '#475569', 'train');
    PERFORM upsert_category('Fire & Smoke',       '#ef4444', 'flame');
    PERFORM upsert_category('Flood Water',        '#3b82f6', 'waves');
    PERFORM upsert_category('Shops',              '#e879f9', 'store');
    PERFORM upsert_category('Warehouses',         '#a78bfa', 'warehouse');
    PERFORM upsert_category('Pipelines',          '#2dd4bf', 'pipette');
    PERFORM upsert_category('Street Lights',      '#fde68a', 'lamp-floor');
END;
$$;
