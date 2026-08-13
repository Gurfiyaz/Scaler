"""Health Check API Endpoint."""

from fastapi import APIRouter
from app.schemas.api_models import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Safe system health check endpoint."""
    return HealthResponse(status="ok", service="PII Redaction Tool")
