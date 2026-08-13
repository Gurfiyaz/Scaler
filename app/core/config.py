"""Application configuration settings."""

import os
from typing import List


class Settings:
    """Central configuration class for PII Redaction Tool."""

    @property
    def app_name(self) -> str:
        return os.getenv("APP_NAME", "PII Redaction Tool")

    @property
    def app_env(self) -> str:
        return os.getenv("APP_ENV", "development").lower()

    @property
    def debug(self) -> bool:
        # Debug defaults to False in production unless explicitly overridden
        default_val = "true" if self.app_env != "production" else "false"
        return os.getenv("APP_DEBUG", default_val).lower() in ("true", "1", "yes")

    @property
    def host(self) -> str:
        return os.getenv("HOST", "0.0.0.0")

    @property
    def port(self) -> int:
        return int(os.getenv("PORT", "8000"))

    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def mask_log_pii(self) -> bool:
        return os.getenv("MASK_LOG_PII", "true").lower() in ("true", "1", "yes")

    @property
    def max_upload_size_mb(self) -> int:
        return int(os.getenv("MAX_UPLOAD_SIZE_MB", "20"))

    @property
    def allowed_extensions(self) -> tuple[str, ...]:
        return (".docx",)

    @property
    def download_ttl_seconds(self) -> int:
        return int(os.getenv("DOWNLOAD_TTL_SECONDS", "600"))

    @property
    def allowed_origins(self) -> List[str]:
        return [
            o.strip()
            for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
            if o.strip()
        ]


settings = Settings()
