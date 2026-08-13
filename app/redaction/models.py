"""Data models for DOCX redaction tasks and execution results."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from app.detection.models import PIIType
from app.ingestion.models import SourceLocation


@dataclass
class RedactionTask:
    """Represents an individual text replacement task within a paragraph."""
    paragraph_index: int
    start_offset: int
    end_offset: int
    original_text: str
    replacement_text: str
    entity_type: PIIType
    location: SourceLocation
    run_indices: List[int] = field(default_factory=list)


@dataclass
class RedactionResult:
    """Summary result returned after executing document redaction and validation."""
    total_detections: int
    replacements_applied: int
    output_path: str
    is_valid_docx: bool
    residual_pii_clean: bool
    timing: Dict[str, float] = field(default_factory=dict)
