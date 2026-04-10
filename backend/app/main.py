import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import calls, dashboard, employees, exports, scripts, webhooks
from app.config import settings
from app.services.storage import storage_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    storage_service.init_bucket()
    yield
    # Shutdown


app = FastAPI(
    title="Call Analytics - Анализ звонков отдела продаж",
    description="Система автоматизированного аудита звонков из Битрикс24",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(exports.router)
app.include_router(calls.router)
app.include_router(employees.router)
app.include_router(scripts.router)
app.include_router(dashboard.router)
app.include_router(webhooks.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
