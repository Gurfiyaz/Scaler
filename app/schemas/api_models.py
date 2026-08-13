"""API response and request Pydantic schemas."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Safe response model for /health endpoint."""

    status: str = Field(..., json_schema_extra={"example": "ok"})
    service: str = Field(..., json_schema_extra={"example": "PII Redaction Tool"})


class InfoResponse(BaseModel):
    """Safe response model for /api/info endpoint."""

    name: str = Field(..., json_schema_extra={"example": "PII Redaction Tool"})
    version: str = Field(..., json_schema_extra={"example": "1.0.0"})
    supported_file_type: str = Field(..., json_schema_extra={"example": ".docx"})
    pii_categories: List[str] = Field(
        ...,
        json_schema_extra={
            "example": [
                "PERSON",
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "ORGANIZATION",
                "ADDRESS",
                "SSN",
                "CREDIT_CARD",
                "DATE_OF_BIRTH",
                "IP_ADDRESS",
            ]
        },
    )


class ValidationSummary(BaseModel):
    """Validation flags for document structure and residual PII safety."""

    document_valid: bool = Field(..., description="True if output is a structurally valid DOCX file.")
    original_pii_residual_check: bool = Field(
        ..., description="True if 0 detected original PII strings remain in redacted text."
    )
    original_file_hash_unchanged: bool = Field(
        ..., description="True if input file hash was preserved 100% byte-for-byte."
    )
    replacement_consistency: bool = Field(
        ..., description="True if replacements_applied == total_detections."
    )


class CategoryMetricsSummary(BaseModel):
    """Per-category evaluation metrics — safe, no raw PII."""

    category: str
    ground_truth_count: int = 0
    predicted_count: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    exact_span_match: Optional[float] = None
    notes: str = ""


class EvaluationSummary(BaseModel):
    """Evaluation report returned in the API response — safe aggregate metrics."""

    available: bool = Field(..., description="True if independent ground truth was available.")
    document_type: str = Field(
        ..., description="'controlled' (has GT) or 'user_uploaded' (no GT)."
    )
    ground_truth_unavailable_reason: Optional[str] = Field(
        None, description="Explanation when GT is unavailable."
    )
    per_category: List[CategoryMetricsSummary] = Field(default_factory=list)

    # Overall metrics — None when GT unavailable
    micro_precision: Optional[float] = None
    micro_recall: Optional[float] = None
    micro_f1: Optional[float] = None
    macro_precision: Optional[float] = None
    macro_recall: Optional[float] = None
    macro_f1: Optional[float] = None
    overall_exact_match_ratio: Optional[float] = None
    accuracy_note: str = (
        "N/A — True-negative population unavailable for sparse span extraction. "
        "Conventional accuracy cannot be calculated without an enumerated TN set."
    )

    # Error analysis — safe aggregates, no raw PII
    total_fp: int = 0
    total_fn: int = 0
    fp_by_category: Dict[str, int] = Field(default_factory=dict)
    fn_by_category: Dict[str, int] = Field(default_factory=dict)


class DetectionAuditEntry(BaseModel):
    """Safe per-detection audit record: category + location only, never raw text."""

    category: str
    paragraph_index: int
    location_type: str = "body"
    recognizer: str


class ProcessResponse(BaseModel):
    """Safe aggregate response returned after processing a document."""

    status: str = Field(..., json_schema_extra={"example": "completed"})
    filename: str = Field(..., json_schema_extra={"example": "redacted_prospectus.docx"})
    detections: Dict[str, int] = Field(..., description="Aggregate count of detected entities per category.")
    total_detections: int = Field(..., json_schema_extra={"example": 12})
    replacements_applied: int = Field(..., json_schema_extra={"example": 12})
    validation: ValidationSummary
    download_id: str = Field(..., description="Secure UUID download token.")
    timing_ms: Dict[str, float] = Field(..., description="Execution duration breakdown in milliseconds.")

    # Evaluation
    evaluation: EvaluationSummary = Field(..., description="Evaluation report with GT metrics where available.")

    # Safe per-detection audit (category + paragraph_index only — no text, no char offsets)
    detection_audit: List[DetectionAuditEntry] = Field(
        default_factory=list,
        description="Safe per-detection audit list for FP/FN investigation — no raw PII."
    )


class ErrorResponse(BaseModel):
    """Generic safe error response model."""

    error: str = Field(..., json_schema_extra={"example": "Invalid document"})
    message: str = Field(..., json_schema_extra={"example": "Please upload a valid DOCX file."})
