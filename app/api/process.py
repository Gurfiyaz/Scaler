"""Document Processing and Redacted Download Endpoints."""

import re
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from starlette.concurrency import run_in_threadpool

from app.schemas.api_models import ErrorResponse, ProcessResponse
from app.services.processing_service import processing_service

router = APIRouter(prefix="/api", tags=["Redaction"])


@router.post(
    "/process",
    response_model=ProcessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid document or bad request."},
        413: {"model": ErrorResponse, "description": "File exceeds maximum upload size limit."},
        500: {"model": ErrorResponse, "description": "Internal document processing error."},
    },
)
async def process_document(file: UploadFile = File(...)) -> ProcessResponse:
    """Accept a .docx upload, run PII redaction pipeline, and return safe aggregate results."""
    filename = file.filename or "uploaded_document.docx"
    
    # Path traversal validation on filename
    if ".." in filename or "/" in filename or "\\" in filename:
        filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)

    content = await file.read()
    return await run_in_threadpool(processing_service.process_document, filename, content)


@router.get(
    "/download/{download_id}",
    response_class=FileResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Download token invalid or expired."},
    },
)
async def download_redacted_document(download_id: str) -> FileResponse:
    """Stream temporary redacted DOCX file associated with a valid download token."""
    # Prevent path traversal in token format
    if not re.match(r"^[a-f0-9\-]{36}$", download_id.lower()):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Not found", "message": "Invalid download token format."},
        )

    filepath, filename = processing_service.get_redacted_file(download_id)

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
