"""spaCy Named Entity Recognition (NER) module for PERSON, ORGANIZATION, and LOCATION."""

import re
from typing import List, Optional
import spacy
from spacy.language import Language

from app.core.logging_config import logger
from app.detection.context_rules import ContextRulesRecognizer
from app.detection.models import PIIDetection, PIIType
from app.ingestion.models import ParagraphModel


class NERRecognizer:
    """Named Entity Recognition engine using spaCy en_core_web_sm model."""

    # Corporate legal suffixes for ORGANIZATION candidate detection
    CORP_SUFFIX_PATTERN = re.compile(
        r"\b[A-Z][A-Za-z0-9&\s]{1,40}\s+(?:Pvt\.?\s*Ltd\.?|Ltd\.?|Inc\.?|Corp\.?|Corporation|LLP|LLC|Labs|Technologies|Services)\b",
        re.IGNORECASE,
    )

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self.nlp: Optional[Language] = None
        self.context_rules = ContextRulesRecognizer()
        self._load_model()

    def _load_model(self):
        """Safely load the spaCy NLP pipeline."""
        try:
            self.nlp = spacy.load(self.model_name)
        except Exception as err:
            logger.warning(f"Failed to load spaCy model '{self.model_name}': {err}. Retrying with disable=['parser']...")
            try:
                self.nlp = spacy.load(self.model_name, disable=["parser"])
            except Exception as err2:
                logger.error(f"Critical error loading spaCy model '{self.model_name}': {err2}")
                self.nlp = None

    def detect_in_paragraph(self, paragraph: ParagraphModel) -> List[PIIDetection]:
        """Extract PERSON, ORGANIZATION, and LOCATION entities using spaCy NLP + Suffix rules."""
        text = paragraph.reconstructed_text
        p_idx = paragraph.paragraph_index
        loc = paragraph.location
        detections: List[PIIDetection] = []

        if not text.strip() or self.context_rules.is_excluded_heading(text):
            return detections

        # 1. Corporate Suffix Rule Matching (High precision ORGANIZATION candidates)
        for match in self.CORP_SUFFIX_PATTERN.finditer(text):
            val = match.group(0).strip()
            if not self.context_rules.is_excluded_heading(val):
                start = match.start()
                end = match.end()
                detections.append(
                    PIIDetection(
                        entity_type=PIIType.ORGANIZATION,
                        start=start,
                        end=end,
                        text=val,
                        recognizer="spacy_corp_suffix",
                        confidence=0.92,
                        paragraph_index=p_idx,
                        location=loc,
                    )
                )

        # 2. spaCy Model Entity Parsing
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                val = ent.text.strip()
                start = ent.start_char
                end = ent.end_char

                # Filter excluded terms or single-character entities
                if len(val) <= 1 or self.context_rules.is_excluded_heading(val):
                    continue

                if ent.label_ == "PERSON":
                    # Reject single capitalized words if they look like common task terms
                    if val in {"Task", "Background", "Deliverables", "Time", "Recall", "Precision"}:
                        continue
                    detections.append(
                        PIIDetection(
                            entity_type=PIIType.PERSON,
                            start=start,
                            end=end,
                            text=val,
                            recognizer="spacy_ner_person",
                            confidence=0.88,
                            paragraph_index=p_idx,
                            location=loc,
                        )
                    )
                elif ent.label_ == "ORG":
                    if val.lower() in {
                        "company", "issuer", "applicant", "the company",
                        "pii", "docx", "readme", "ssn", "ip", "json", "html",
                        "css", "api", "url", "pdf", "vcf", "assignment", "requirements", "ner"
                    }:
                        continue
                    detections.append(
                        PIIDetection(
                            entity_type=PIIType.ORGANIZATION,
                            start=start,
                            end=end,
                            text=val,
                            recognizer="spacy_ner_org",
                            confidence=0.85,
                            paragraph_index=p_idx,
                            location=loc,
                        )
                    )
                elif ent.label_ in ("GPE", "LOC"):
                    # Require at least 2 tokens OR a digit present (postal codes, building numbers)
                    # to suppress single-word city/country names (e.g. "India", "Delhi")
                    token_count = len(val.split())
                    has_digit = any(ch.isdigit() for ch in val)
                    if token_count < 2 and not has_digit:
                        continue
                    detections.append(
                        PIIDetection(
                            entity_type=PIIType.ADDRESS,
                            start=start,
                            end=end,
                            text=val,
                            recognizer="spacy_ner_loc",
                            confidence=0.75,
                            paragraph_index=p_idx,
                            location=loc,
                        )
                    )

        return detections
