"""FastAPI Application Main Entry Point."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# 2. Custom Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# 3. Register API Routers
app.include_router(health_router)
app.include_router(info_router)
app.include_router(process_router)

# 4. Mount Frontend Static Files at Root
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
