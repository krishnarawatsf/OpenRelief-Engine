from typing import Any


async def find_nearest_responder(db: Any, lat: float, lon: float, unit_type: str) -> Any | None:
    return await db.fetchrow(
        """
        SELECT id, unit_name, unit_type,
            ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon,
            ST_Distance(
                location, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
            ) / 1000.0 AS distance_km
        FROM responders
        WHERE is_available = TRUE AND unit_type = $3::responder_unit_type
        ORDER BY location <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
        LIMIT 1
        FOR UPDATE SKIP LOCKED
        """,
        lon,
        lat,
        unit_type,
    )
