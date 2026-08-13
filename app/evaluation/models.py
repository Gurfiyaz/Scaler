"""Data models for PII evaluation and ground truth annotation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from app.detection.models import PIIType
from app.ingestion.models import SourceLocation


@dataclass
class GroundTruthAnnotation:
    """Represents a manually verified ground-truth PII span."""
    entity_type: PIIType
    start: int  # Inclusive start character index in paragraph reconstructed text
    end: int    # Exclusive end character index in paragraph reconstructed text
    paragraph_index: int
    annotation_id: str = ""
    location: Optional[SourceLocation] = None
    text_sha256: Optional[str] = None  # Privacy-preserving SHA-256 digest of original text
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GroundTruthDocument:
    """Represents the complete ground-truth annotations for a document."""
    document_id: str
    annotations: List[GroundTruthAnnotation] = field(default_factory=list)
    created_at: str = ""
    annotator_id: str = "human_annotator"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CategoryMetrics:
    """Per-category evaluation metrics."""
    category: PIIType
    ground_truth_count: int = 0
    predicted_count: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    exact_match_ratio: float = 0.0  # Jaccard-style span match ratio: TP / (TP + FP + FN)
    notes: str = ""


@dataclass
class EvaluationReport:
    """Overall document evaluation summary report."""
    document_id: str
    per_category: Dict[PIIType, CategoryMetrics] = field(default_factory=dict)
    total_ground_truth: int = 0
    total_predictions: int = 0
    total_tp: int = 0
    total_fp: int = 0
    total_fn: int = 0
    micro_precision: float = 0.0
    micro_recall: float = 0.0
    micro_f1: float = 0.0
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1: float = 0.0
    overall_exact_match_ratio: float = 0.0  # Jaccard-style set similarity: TP / (TP + FP + FN)
    error_analysis: Dict[str, Any] = field(default_factory=dict)
