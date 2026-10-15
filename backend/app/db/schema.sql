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
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE incidents
    ADD COLUMN IF NOT EXISTS extracted_location_name VARCHAR(255) NOT NULL
    DEFAULT 'SRM Institute of Science and Technology, Kattankulathur';

CREATE INDEX IF NOT EXISTS responders_location_gist ON responders USING GIST (location);
CREATE INDEX IF NOT EXISTS incidents_location_gist ON incidents USING GIST (location);
