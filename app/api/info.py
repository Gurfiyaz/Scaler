"""Application Metadata Info API Endpoint."""

from fastapi import APIRouter
from app.detection.models import PIIType
from app.schemas.api_models import InfoResponse

router = APIRouter(prefix="/api", tags=["Information"])


@router.get("/info", response_model=InfoResponse)
async def get_app_info() -> InfoResponse:
    """Return non-sensitive application capabilities and supported categories."""
    return InfoResponse(
        name="PII Redaction Tool",
        version="1.0.0",
        supported_file_type=".docx",
        pii_categories=[c.value for c in PIIType],
    )
