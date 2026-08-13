"""Standard logging configuration module for PII Redaction Tool.

DEVELOPER PRIVACY GUIDELINE:
Future document-processing, detection, and redaction modules MUST NOT pass raw PII
strings or unredacted document content into log calls.
Only high-level metadata (e.g. processing time, file size, counts of detected entities)
may be logged.
"""

import logging
import sys
from app.core.config import settings


def setup_logging() -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("pii_redactor")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Prevent duplicate handlers if re-initialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()

