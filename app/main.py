"""FastAPI Application Main Entry Point."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import health_router, info_router, process_router
from app.core.config import settings
from app.core.logging_config import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup & shutdown events."""
    logger.info("Initializing PII Redaction Tool service...")
    logger.info(f"Environment: {settings.app_env} | Debug: {settings.debug}")
    yield
    logger.info("Shutting down PII Redaction Tool service.")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Professional PII Redaction Tool for Scaler AI Labs Assessment",
    docs_url="/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
)

# 1. CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all in production; tighten via ALLOWED_ORIGINS env var if needed
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# 2. Global Exception Handlers — ensure ALL errors return valid JSON, never empty body
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return structured JSON for all HTTP errors — prevents SyntaxError: Unexpected end of JSON."""
    detail = exc.detail
    if isinstance(detail, dict):
        error = detail.get("error", "Error")
        message = detail.get("message", str(exc.detail))
    else:
        error = f"HTTP {exc.status_code}"
        message = str(detail) if detail else "An error occurred."
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error, "message": message},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured JSON for Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "message": "Invalid request format."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler — ensures unhandled exceptions return JSON not an empty 500 body."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {type(exc).__name__}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Processing Error",
            "message": "An internal error occurred while processing the document. Please try again.",
        },
    )


# 3. Custom Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# 4. Register API Routers
app.include_router(health_router)
app.include_router(info_router)
app.include_router(process_router)

# 5. Explicitly serve index.html on root to prevent README.md fallback
frontend_dir = Path(__file__).parent.parent / "frontend"


@app.get("/")
async def serve_index():
    from fastapi.responses import FileResponse
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"error": "Not found", "message": "Frontend not found."})


# Mount the rest of the frontend assets (css, js)
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir)), name="frontend_assets")
