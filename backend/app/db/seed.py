import asyncio
import os
from uuid import UUID

import asyncpg
from dotenv import load_dotenv

RESPONDERS = [
    (UUID("00000000-0000-4000-8000-000000000001"), "SRM Ambulance 1", "AMBULANCE", 12.8218, 80.0428),
    (UUID("00000000-0000-4000-8000-000000000002"), "SRM Ambulance 2", "AMBULANCE", 12.8245, 80.0470),
    (UUID("00000000-0000-4000-8000-000000000003"), "SRM Fire Truck 1", "FIRE_TRUCK", 12.8202, 80.0461),
    (UUID("00000000-0000-4000-8000-000000000004"), "SRM Fire Truck 2", "FIRE_TRUCK", 12.8260, 80.0418),
    (UUID("00000000-0000-4000-8000-000000000005"), "SRM Police Unit 1", "POLICE", 12.8227, 80.0482),
    (UUID("00000000-0000-4000-8000-000000000006"), "SRM Police Unit 2", "POLICE", 12.8251, 80.0399),
]


async def seed() -> None:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set before running the responder seed.")
    connection = await asyncpg.connect(database_url)
    try:
        for responder_id, name, unit_type, latitude, longitude in RESPONDERS:
            await connection.execute(
                """
                INSERT INTO responders (id, unit_name, unit_type, location, is_available, updated_at)
                VALUES ($1, $2, $3::responder_unit_type,
                    ST_SetSRID(ST_MakePoint($4, $5), 4326)::geography, TRUE, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    unit_name = EXCLUDED.unit_name,
                    unit_type = EXCLUDED.unit_type,
                    location = EXCLUDED.location,
                    is_available = TRUE,
                    updated_at = NOW()
                """,
                responder_id,
                name,
                unit_type,
                longitude,
                latitude,
            )
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(seed())
