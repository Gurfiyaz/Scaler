"""API routes package."""

from app.api.health import router as health_router
from app.api.info import router as info_router
from app.api.process import router as process_router

__all__ = ["health_router", "info_router", "process_router"]
