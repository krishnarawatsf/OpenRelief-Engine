import os

import asyncpg
from fastapi import HTTPException

_pool: asyncpg.Pool | None = None


async def open_pool() -> asyncpg.Pool:
    global _pool
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be configured before connecting to PostgreSQL.")
    _pool = await asyncpg.create_pool(database_url)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def require_pool() -> asyncpg.Pool:
    if _pool is None:
        raise HTTPException(
            status_code=503,
            detail="Database is not connected. Set DATABASE_URL and restart the backend.",
        )
    return _pool
