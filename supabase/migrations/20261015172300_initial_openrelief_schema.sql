CREATE EXTENSION IF NOT EXISTS postgis;

DO $$
BEGIN
    CREATE TYPE responder_unit_type AS ENUM ('AMBULANCE', 'FIRE_TRUCK', 'POLICE');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS responders (
    id UUID PRIMARY KEY,
    unit_name VARCHAR(120) NOT NULL,
    unit_type responder_unit_type NOT NULL,
    location GEOGRAPHY(Point, 4326) NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY,
    transcript TEXT NOT NULL,
    incident_type VARCHAR(80) NOT NULL,
    extracted_location_name VARCHAR(255) NOT NULL DEFAULT 'SRM Institute of Science and Technology, Kattankulathur',
    urgency_rating INT NOT NULL CHECK (urgency_rating BETWEEN 1 AND 5),
    casualty_count INT NOT NULL CHECK (casualty_count >= 0),
    priority_score DOUBLE PRECISION NOT NULL,
    cap_severity VARCHAR(20) NOT NULL
        CHECK (cap_severity IN ('Extreme', 'Severe', 'Moderate', 'Minor')),
    location GEOGRAPHY(Point, 4326) NOT NULL,
    assigned_responder_id UUID REFERENCES responders(id),
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN'
        CONSTRAINT incidents_status_lifecycle_check
        CHECK (status IN ('OPEN', 'DISPATCHED', 'RESOLVED', 'CANCELLED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS extracted_location_name VARCHAR(255) NOT NULL
    DEFAULT 'SRM Institute of Science and Technology, Kattankulathur';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'incidents_status_lifecycle_check'
          AND conrelid = 'incidents'::regclass
    ) THEN
        ALTER TABLE incidents
            ADD CONSTRAINT incidents_status_lifecycle_check
            CHECK (status IN ('OPEN', 'DISPATCHED', 'RESOLVED', 'CANCELLED'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS responders_location_gist ON responders USING GIST (location);
CREATE INDEX IF NOT EXISTS incidents_location_gist ON incidents USING GIST (location);
CREATE INDEX IF NOT EXISTS incidents_active_priority
    ON incidents (priority_score DESC, created_at DESC)
    WHERE status IN ('OPEN', 'DISPATCHED');

INSERT INTO responders (id, unit_name, unit_type, location, is_available, updated_at)
VALUES
    ('00000000-0000-4000-8000-000000000001', 'SRM Ambulance 1', 'AMBULANCE',
        ST_SetSRID(ST_MakePoint(80.0428, 12.8218), 4326)::geography, TRUE, NOW()),
    ('00000000-0000-4000-8000-000000000002', 'SRM Ambulance 2', 'AMBULANCE',
        ST_SetSRID(ST_MakePoint(80.0470, 12.8245), 4326)::geography, TRUE, NOW()),
    ('00000000-0000-4000-8000-000000000003', 'SRM Fire Truck 1', 'FIRE_TRUCK',
        ST_SetSRID(ST_MakePoint(80.0461, 12.8202), 4326)::geography, TRUE, NOW()),
    ('00000000-0000-4000-8000-000000000004', 'SRM Fire Truck 2', 'FIRE_TRUCK',
        ST_SetSRID(ST_MakePoint(80.0418, 12.8260), 4326)::geography, TRUE, NOW()),
    ('00000000-0000-4000-8000-000000000005', 'SRM Police Unit 1', 'POLICE',
        ST_SetSRID(ST_MakePoint(80.0482, 12.8227), 4326)::geography, TRUE, NOW()),
    ('00000000-0000-4000-8000-000000000006', 'SRM Police Unit 2', 'POLICE',
        ST_SetSRID(ST_MakePoint(80.0399, 12.8251), 4326)::geography, TRUE, NOW())
ON CONFLICT (id) DO UPDATE SET
    unit_name = EXCLUDED.unit_name,
    unit_type = EXCLUDED.unit_type,
    location = EXCLUDED.location,
    updated_at = NOW();
