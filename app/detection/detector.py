"""Master PII Detection Engine Orchestrator."""

from typing import Dict, List, Union
from app.core.logging_config import logger
from app.detection.context_rules import ContextRulesRecognizer
from app.detection.models import PIIDetection, PIIType
from app.detection.ner_recognizer import NERRecognizer
from app.detection.regex_recognizer import RegexRecognizer
from app.detection.span_resolver import SpanResolver
from app.ingestion.models import DocumentModel, ParagraphModel
from app.ingestion.run_mapper import RunMapper


class PIIDetector:
    """Read-only multi-layer PII detection engine orchestrator."""

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        self.regex_recognizer = RegexRecognizer()
        self.ner_recognizer = NERRecognizer(model_name=spacy_model)
        self.context_recognizer = ContextRulesRecognizer()
        self.span_resolver = SpanResolver()

    def detect_in_document(self, document: DocumentModel) -> List[PIIDetection]:
        """Detect all PII entities across document body paragraphs, tables, headers, and footers.

        Args:
            document: DocumentModel instance from Phase 3 DOCXParser.

        Returns:
            List of deduplicated, normalized PIIDetection objects.
        """
        all_detections: List[PIIDetection] = []

        # Collect all paragraph models
        all_paragraphs: List[ParagraphModel] = list(document.paragraphs)

        # Include table cell paragraphs
        for tbl in document.tables:
            for row in tbl.rows:
                for cell in row.cells:
                    all_paragraphs.extend(cell.paragraphs)

        # Include header paragraphs
        for hdr in document.headers:
            all_paragraphs.extend(hdr.paragraphs)

        # Include footer paragraphs
        for ftr in document.footers:
            all_paragraphs.extend(ftr.paragraphs)

        for p_model in all_paragraphs:
            p_dets = self.detect_in_paragraph(p_model)
            all_detections.extend(p_dets)

        # Safe privacy logging: Log ONLY counts by category, NEVER raw text
        counts = self.get_safe_detection_counts(all_detections)
        logger.info(f"PII Detection Complete. Total Entities Detected: {len(all_detections)} | Counts: {counts}")

        return all_detections

    def detect_in_paragraph(self, paragraph: ParagraphModel) -> List[PIIDetection]:
        """Detect PII entities within a single reconstructed paragraph."""
        text = paragraph.reconstructed_text
        if not text.strip():
            return []

        candidates: List[PIIDetection] = []

        # 1. Layer 1: Structured Regex Recognizer (Email, Phone, IP, Credit Card, SSN)
        regex_dets = self.regex_recognizer.detect_in_paragraph(paragraph)
        candidates.extend(regex_dets)

        # 2. Layer 2: Contextual Recognizer (DOB, Address)
        dob_dets = self.context_recognizer.detect_dob(paragraph)
        candidates.extend(dob_dets)

        addr_dets = self.context_recognizer.detect_address(paragraph)
        candidates.extend(addr_dets)

        # 3. Layer 3: spaCy NER Recognizer (Person, Organization, Location)
        ner_dets = self.ner_recognizer.detect_in_paragraph(paragraph)
        candidates.extend(ner_dets)

        # 4. Normalize & Resolve Overlaps
        resolved_dets = self.span_resolver.resolve_overlaps(candidates, text)

        # 5. Map character offsets back to run indices using RunMapper
        final_dets: List[PIIDetection] = []
        for det in resolved_dets:
            overlapping_runs = RunMapper.map_span_to_runs(paragraph, det.start, det.end)
            run_indices = [r.run_index for r in overlapping_runs]

            mapped_det = PIIDetection(
                entity_type=det.entity_type,
                start=det.start,
                end=det.end,
                text=det.text,
                recognizer=det.recognizer,
                confidence=det.confidence,
                paragraph_index=paragraph.paragraph_index,
                location=paragraph.location,
                run_indices=run_indices,
                metadata=det.metadata,
            )
            final_dets.append(mapped_det)

        return final_dets

    @staticmethod
    def get_safe_detection_counts(detections: List[PIIDetection]) -> Dict[str, int]:
        """Return safe aggregated entity counts by category without exposing PII strings."""
        counts: Dict[str, int] = {pii_type.value: 0 for pii_type in PIIType}
        for det in detections:
            cat_name = det.entity_type.value
            counts[cat_name] = counts.get(cat_name, 0) + 1
        return counts
