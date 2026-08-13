"""Data models for entity mapping registry records."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from app.detection.models import PIIType


@dataclass(frozen=True)
class EntityMappingKey:
    """Immutable dictionary key for identifying an entity mapping."""
    entity_type: PIIType
    normalized_original: str


@dataclass
class EntityMappingRecord:
    """Represents a mapped pair between an original PII value and its fake replacement."""
    original_value: str
    normalized_original: str
    entity_type: PIIType
    replacement_value: str
    seed_hash: str  # SHA-256 fingerprint digest used for seeding
    associated_person_name: Optional[str] = None
    creation_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
