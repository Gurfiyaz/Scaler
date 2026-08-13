"""Processing Service orchestrating DOCX parsing, detection, mapping, and redaction.

Ensures zero raw PII leakage, safe temporary file lifecycles, and tokenized output retrieval.
"""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
import time
from typing import Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging_config import logger
from app.detection.detector import PIIDetector
from app.detection.models import PIIDetection, PIIType
from app.evaluation.evaluator import Evaluator
from app.evaluation.ground_truth import GroundTruthManager
from app.ingestion.docx_parser import DOCXParser
from app.ingestion.exceptions import IngestionError
from app.mapping.entity_mapper import EntityMapper
from app.redaction.docx_redactor import DOCXRedactor
from app.schemas.api_models import (
    CategoryMetricsSummary,
    DetectionAuditEntry,
    EvaluationSummary,
    ProcessResponse,
    ValidationSummary,
)

# ──────────────────────────────────────────────
# Documents with independently annotated ground truth
# Maps: exact filename → path to GT JSON file
# ──────────────────────────────────────────────
_GROUND_TRUTH_REGISTRY: Dict[str, Path] = {
    "enterprise data - assignment.docx": Path(__file__).parent.parent.parent
    / "private_data"
    / "ground_truth.json",
    "pii_redaction_test.docx": Path(__file__).parent.parent.parent
    / "tests"
    / "fixtures"
    / "pii_redaction_test_ground_truth.json",
}

# All 9 canonical PII categories in display order
_ALL_CATEGORIES: List[PIIType] = list(PIIType)


@dataclass
class DownloadRecord:
    """Internal record for ephemeral download file storage."""

    filepath: Path
    filename: str
    created_at: float


class DocumentProcessingService:
    """Service layer executing privacy redaction pipeline and managing download tokens."""

    def __init__(self):
        self.parser = DOCXParser()
        self.detector = PIIDetector()
        self.mapper = EntityMapper()
        self.redactor = DOCXRedactor()
        self.evaluator = Evaluator()
        self._downloads: Dict[str, DownloadRecord] = {}

    def validate_file_header(self, filename: str, content: bytes) -> None:
        """Validate filename extension, file size, and ZIP header magic bytes."""
        if not filename or not filename.lower().endswith(".docx"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid document", "message": "Please upload a valid .docx file."},
            )

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "File too large",
                    "message": f"Document exceeds maximum allowed size of {settings.max_upload_size_mb} MB.",
                },
            )

        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Empty file", "message": "Uploaded file is empty."},
            )

        # Validate ZIP magic bytes (PK\x03\x04)
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid document", "message": "File is not a valid DOCX container."},
            )

    def process_document(self, filename: str, content: bytes) -> ProcessResponse:
        """Execute full redaction pipeline on uploaded content and return safe aggregate results."""
        self.validate_file_header(filename, content)
        self.cleanup_expired_downloads()

        # Compute SHA-256 hash of original input
        input_hash = hashlib.sha256(content).hexdigest()

        # Create temporary input file
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_in:
            tmp_in.write(content)
            tmp_in_path = Path(tmp_in.name)

        # Create temporary output file path
        tmp_out_fd, tmp_out_path_str = tempfile.mkstemp(suffix=".docx")
        os.close(tmp_out_fd)
        tmp_out_path = Path(tmp_out_path_str)

        try:
            logger.info("Processing document upload...")

            # ── Step 1: Ingestion ──────────────────────────
            t0 = time.perf_counter()
            doc_model = self.parser.parse_document(tmp_in_path)
            t_parse = (time.perf_counter() - t0) * 1000

            # ── Step 2: Detection ──────────────────────────
            t0 = time.perf_counter()
            detections = self.detector.detect_in_document(doc_model)
            t_detect = (time.perf_counter() - t0) * 1000

            # ── Step 3: Mapping ────────────────────────────
            t0 = time.perf_counter()
            mappings = self.mapper.map_all_detections(detections)
            t_map = (time.perf_counter() - t0) * 1000

            # ── Step 4: Redaction ──────────────────────────
            t0 = time.perf_counter()
            redaction_result = self.redactor.redact_document(tmp_in_path, tmp_out_path, detections, mappings)
            t_redact = (time.perf_counter() - t0) * 1000

            # ── Step 5: Validation ─────────────────────────
            t0 = time.perf_counter()
            with open(tmp_in_path, "rb") as f:
                input_hash_after = hashlib.sha256(f.read()).hexdigest()
            input_unchanged = input_hash == input_hash_after
            replacement_consistency = redaction_result.replacements_applied == len(detections)
            t_validate = (time.perf_counter() - t0) * 1000

            # ── Step 6: Evaluation ─────────────────────────
            t0 = time.perf_counter()
            evaluation_summary = self._run_evaluation(filename, detections)
            t_eval = (time.perf_counter() - t0) * 1000

            # ── Aggregate category counts ──────────────────
            counts: Dict[str, int] = {}
            for d in detections:
                cat = d.entity_type.value
                counts[cat] = counts.get(cat, 0) + 1

            # ── Safe per-detection audit ───────────────────
            detection_audit = self._build_audit(detections)

            # ── Download token ─────────────────────────────
            download_id = str(uuid.uuid4())
            safe_out_name = f"redacted_{Path(filename).name}"

            self._downloads[download_id] = DownloadRecord(
                filepath=tmp_out_path,
                filename=safe_out_name,
                created_at=time.time(),
            )

            logger.info(
                f"Document processing completed. Total detections: {len(detections)}. "
                f"Download ID: {download_id}"
            )

            total_time = round(t_parse + t_detect + t_map + t_redact + t_validate + t_eval, 2)

            return ProcessResponse(
                status="completed",
                filename=safe_out_name,
                detections=counts,
                total_detections=len(detections),
                replacements_applied=redaction_result.replacements_applied,
                validation=ValidationSummary(
                    document_valid=redaction_result.is_valid_docx,
                    original_pii_residual_check=redaction_result.residual_pii_clean,
                    original_file_hash_unchanged=input_unchanged,
                    replacement_consistency=replacement_consistency,
                ),
                download_id=download_id,
                timing_ms={
                    "parsing": round(t_parse, 2),
                    "detection": round(t_detect, 2),
                    "mapping": round(t_map, 2),
                    "redaction": round(t_redact, 2),
                    "validation": round(t_validate, 2),
                    "evaluation": round(t_eval, 2),
                    "total": total_time,
                },
                evaluation=evaluation_summary,
                detection_audit=detection_audit,
            )

        except IngestionError as err:
            if tmp_out_path.exists():
                tmp_out_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "Invalid document", "message": str(err)},
            )
        except Exception as err:
            if tmp_out_path.exists():
                tmp_out_path.unlink()
            logger.error(f"Unexpected processing error: {type(err).__name__}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "Processing error", "message": "An internal error occurred while processing the document."},
            )
        finally:
            # Always clean up temporary input file immediately
            if tmp_in_path.exists():
                tmp_in_path.unlink()

    # ──────────────────────────────────────────────────────────────────────
    # Evaluation helpers
    # ──────────────────────────────────────────────────────────────────────

    def _run_evaluation(self, filename: str, detections: List[PIIDetection]) -> EvaluationSummary:
        """Run formal evaluation when ground truth is available, else return N/A summary."""
        norm_name = filename.strip().lower()
        # Strip 'redacted_' prefix if somehow passed
        if norm_name.startswith("redacted_"):
            norm_name = norm_name[len("redacted_"):]

        gt_path = _GROUND_TRUTH_REGISTRY.get(norm_name)

        if gt_path is None or not gt_path.exists():
            # No independent ground truth — return honest N/A
            return self._build_no_gt_summary(filename)

        try:
            gt_doc = GroundTruthManager.load_from_file(gt_path)
            report = self.evaluator.evaluate(gt_doc, detections)

            # Build per-category list (all 9 shown, even zero entries)
            per_cat: List[CategoryMetricsSummary] = []
            for cat in _ALL_CATEGORIES:
                m = report.per_category.get(cat)
                if m:
                    per_cat.append(CategoryMetricsSummary(
                        category=cat.value,
                        ground_truth_count=m.ground_truth_count,
                        predicted_count=m.predicted_count,
                        tp=m.tp,
                        fp=m.fp,
                        fn=m.fn,
                        precision=m.precision,
                        recall=m.recall,
                        f1=m.f1,
                        exact_span_match=m.exact_match_ratio,
                        notes=m.notes,
                    ))
                else:
                    per_cat.append(CategoryMetricsSummary(
                        category=cat.value,
                        notes="Not present in evaluation document.",
                    ))

            # FP/FN by category from error analysis
            fp_by_cat: Dict[str, int] = {}
            fn_by_cat: Dict[str, int] = {}
            for cat in _ALL_CATEGORIES:
                m = report.per_category.get(cat)
                if m:
                    if m.fp > 0:
                        fp_by_cat[cat.value] = m.fp
                    if m.fn > 0:
                        fn_by_cat[cat.value] = m.fn

            return EvaluationSummary(
                available=True,
                document_type="controlled",
                per_category=per_cat,
                micro_precision=report.micro_precision,
                micro_recall=report.micro_recall,
                micro_f1=report.micro_f1,
                macro_precision=report.macro_precision,
                macro_recall=report.macro_recall,
                macro_f1=report.macro_f1,
                overall_exact_match_ratio=report.overall_exact_match_ratio,
                total_fp=report.total_fp,
                total_fn=report.total_fn,
                fp_by_category=fp_by_cat,
                fn_by_category=fn_by_cat,
            )

        except Exception as err:
            logger.error(f"Evaluation error: {type(err).__name__} — {err}")
            return self._build_no_gt_summary(filename, reason=f"Evaluation error: {type(err).__name__}")

    @staticmethod
    def _build_no_gt_summary(filename: str, reason: Optional[str] = None) -> EvaluationSummary:
        """Build an honest N/A EvaluationSummary when GT is unavailable."""
        per_cat = [
            CategoryMetricsSummary(
                category=cat.value,
                notes="N/A — Independent ground truth unavailable",
            )
            for cat in _ALL_CATEGORIES
        ]
        return EvaluationSummary(
            available=False,
            document_type="user_uploaded",
            ground_truth_unavailable_reason=(
                reason or
                "No independent ground truth exists for this document. "
                "Precision/Recall/F1 cannot be calculated without verified annotations. "
                "Only detector predictions are available."
            ),
            per_category=per_cat,
        )

    @staticmethod
    def _build_audit(detections: List[PIIDetection]) -> List[DetectionAuditEntry]:
        """Build safe per-detection audit list: category + paragraph_index only — no raw text."""
        entries: List[DetectionAuditEntry] = []
        for det in detections:
            loc_type = det.location.location_type.value if det.location else "body"
            entries.append(DetectionAuditEntry(
                category=det.entity_type.value,
                paragraph_index=det.paragraph_index,
                location_type=loc_type,
                recognizer=det.recognizer,
            ))
        return entries

    # ──────────────────────────────────────────────────────────────────────
    # Download management
    # ──────────────────────────────────────────────────────────────────────

    def get_redacted_file(self, download_id: str) -> Tuple[Path, str]:
        """Retrieve temporary output file path for a valid download token."""
        self.cleanup_expired_downloads()

        if download_id not in self._downloads:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Not found", "message": "Download token invalid or expired."},
            )

        record = self._downloads[download_id]
        if not record.filepath.exists():
            del self._downloads[download_id]
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "Not found", "message": "Redacted document file no longer exists."},
            )

        return record.filepath, record.filename

    def cleanup_expired_downloads(self) -> None:
        """Purge temporary download files exceeding download TTL."""
        now = time.time()
        expired_tokens: List[str] = []

        for token, rec in self._downloads.items():
            if now - rec.created_at > settings.download_ttl_seconds:
                expired_tokens.append(token)
                if rec.filepath.exists():
                    try:
                        rec.filepath.unlink()
                    except Exception:
                        pass

        for token in expired_tokens:
            del self._downloads[token]


processing_service = DocumentProcessingService()
