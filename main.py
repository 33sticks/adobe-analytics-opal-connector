"""Adobe Analytics Opal Connector — FastAPI entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.discovery.manifest import get_manifest
from app.tools.referrer_breakdown import router as referrer_router
from app.tools.traffic_analysis import router as traffic_router

app = FastAPI(title="Adobe Analytics Opal Connector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(traffic_router)
app.include_router(referrer_router)


@app.on_event("startup")
async def startup_event() -> None:
    """Log startup confirmation with environment name."""
    settings = get_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
    logger = logging.getLogger(__name__)
    logger.info("Adobe Analytics Opal Connector started", extra={"environment": settings.environment})


@app.get("/")
async def health_check() -> dict:
    """Health check endpoint for Railway and monitoring."""
    return {"status": "healthy", "service": "adobe-analytics-opal-connector"}


@app.get("/discovery")
async def discovery() -> dict:
    """Opal tool manifest — called when registering or syncing the tool."""
    settings = get_settings()
    return get_manifest(settings.base_url)
