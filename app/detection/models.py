"""Data models for PII Detection engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from app.ingestion.models import SourceLocation


class PIIType(str, Enum):
    """Supported PII categories for detection."""
    PERSON = "PERSON"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    ORGANIZATION = "ORGANIZATION"
    ADDRESS = "ADDRESS"
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    IP_ADDRESS = "IP_ADDRESS"


@dataclass
class PIIDetection:
    """Represents a detected PII span within a document paragraph."""
    entity_type: PIIType
    start: int  # Inclusive start offset in paragraph reconstructed text
    end: int  # Exclusive end offset in paragraph reconstructed text
    text: str
    recognizer: str
    confidence: float
    paragraph_index: int
    location: Optional[SourceLocation] = None
    run_indices: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
