"""
main.py
=======
FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import chat, groundwater
from .services.memory import memory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "Backend for INGRES-AI— a conversational assistant over CGWB/INGRES "
        "groundwater data. Fetches records from the National Water Data Portal (or a local "
        "reference dataset) and generates natural-language answers via an LLM API."
    ),
)

# --- CORS --------------------------------------------------------------
# origin/port) call this API from the browser. Allowed origins come from
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["Get, POST, OPTIONS"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(groundwater.router)


@app.get("/", tags=["meta"])
def root():
    return {
        "service": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
        "chat_endpoint": "/api/v1/chat",
    }


@app.get("/health", tags=["meta"])
def health():
    """Quick self-check: confirms the process is up and reports whether each
    external integration is configured, without leaking key values."""
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
        "llm_configured": bool(settings.GROQ_API_KEY),
        "llm_model": settings.GROQ_MODEL,
        "live_water_api_enabled": settings.USE_LIVE_WATER_API,
        "water_data_mode": "live_national_water_data_portal" if settings.USE_LIVE_WATER_API else "local_reference_dataset",
        "cors_allowed_origins": settings.cors_origins,
        "active_chat_sessions": memory.active_session_count(),
    }
