import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.database import close_pool, open_pool

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("DATABASE_URL"):
        await open_pool()
    yield
    await close_pool()


app = FastAPI(title="OpenRelief Engine", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
