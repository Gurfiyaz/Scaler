"""Contextual Rules and Heuristics Recognizer for DOB, Address, and Heading Exclusions."""

import re
from typing import List, Set
from app.detection.models import PIIDetection, PIIType
from app.ingestion.models import ParagraphModel


class ContextRulesRecognizer:
    """Context-driven recognizer for DOB, Address, and Heading Exclusion Filters."""

    # Context keywords triggering Date of Birth classification
    DOB_KEYWORDS = re.compile(
        r"\b(?:dob|date\s+of\s+birth|born\s+on|birth\s*date|age[:\s])\b",
        re.IGNORECASE,
    )

    # Date Formats: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, 15-Jan-1985, 15 Mon YYYY
    DATE_PATTERN = re.compile(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|"
        r"\d{1,2}[\s/-]?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s/-]?\d{2,4}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s/-]?\d{1,2},?[\s/-]?\d{2,4})\b",
        re.IGNORECASE,
    )

    # Address keywords & structural indicators
    ADDRESS_KEYWORDS = re.compile(
        r"\b(?:street|road|avenue|blvd|lane|plot|flat|house|building|suite|apartment|"
        r"nagar|colony|marg|pin|zip|postal\s+code|po\s+box|district|state|andhra\s+pradesh|maharashtra|karnataka|delhi|mumbai|bangalore)\b",
        re.IGNORECASE,
    )

    # Address Pattern: Combination of street/plot/flat, numbers, city, state, pin/zip code
    ADDRESS_PATTERN = re.compile(
        r"\b(?:\d{1,4}[,\s]+)?(?:[A-Z][a-z0-9\.]+[,\s]+){1,5}"
        r"(?:Street|Road|Avenue|Lane|Nagar|Colony|Marg|District|State|Prakasam|Andhra Pradesh|Karnataka|Maharashtra|Delhi)"
        r"(?:[,\s]+\d{5,6})?\b",
        re.IGNORECASE,
    )

    # PIN/ZIP Code pattern: 5 or 6 digits preceded by city/state/pin/zip
    PIN_CODE_PATTERN = re.compile(r"\b(?:pin|zip|code)?\s*(\d{5,6})\b", re.IGNORECASE)

    # Excluded Headings / Task Terms to prevent false positives
    EXCLUDED_TERMS: Set[str] = {
        "assignment:", "assignment", "background", "task", "deliverables",
        "evaluation criteria", "time to complete", "recall:", "precision:",
        "code quality:", "communication:", "company", "issuer", "applicant",
        "prospectus", "red herring prospectus", "order", "ticket"
    }

    def detect_dob(self, paragraph: ParagraphModel) -> List[PIIDetection]:
        """Detect Date of Birth (DOB) ONLY when explicit DOB context keywords exist."""
        text = paragraph.reconstructed_text
        p_idx = paragraph.paragraph_index
        loc = paragraph.location
        detections: List[PIIDetection] = []

        # Check if DOB context keyword is present in paragraph
        if not self.DOB_KEYWORDS.search(text):
            return detections

        # Extract date matches
        for match in self.DATE_PATTERN.finditer(text):
            val = match.group(0).strip()
            start = match.start()
            end = match.end()

            # Verify proximity to DOB keyword (within 50 chars)
            dob_match = self.DOB_KEYWORDS.search(text)
            if dob_match and abs(start - dob_match.start()) <= 60:
                detections.append(
                    PIIDetection(
                        entity_type=PIIType.DATE_OF_BIRTH,
                        start=start,
                        end=end,
                        text=val,
                        recognizer="context_dob",
                        confidence=0.9,
                        paragraph_index=p_idx,
                        location=loc,
                    )
                )

        return detections

    def detect_address(self, paragraph: ParagraphModel) -> List[PIIDetection]:
        """Detect Physical/Mailing Addresses using conservative keyword & pattern heuristics."""
        text = paragraph.reconstructed_text
        p_idx = paragraph.paragraph_index
        loc = paragraph.location
        detections: List[PIIDetection] = []

        # Address detection requires presence of address keywords
        if not self.ADDRESS_KEYWORDS.search(text):
            return detections

        for match in self.ADDRESS_PATTERN.finditer(text):
            val = match.group(0).strip()

            # Exclude short single-word false matches
            if len(val.split()) < 2:
                continue

            start = match.start()
            end = match.end()

            detections.append(
                PIIDetection(
                    entity_type=PIIType.ADDRESS,
                    start=start,
                    end=end,
                    text=val,
                    recognizer="context_address",
                    confidence=0.85,
                    paragraph_index=p_idx,
                    location=loc,
                )
            )

        return detections

    def is_excluded_heading(self, text: str) -> bool:
        """Check if candidate text is a generic document heading or instruction term."""
        clean_text = text.strip().lower()
        if clean_text in self.EXCLUDED_TERMS:
            return True
        for term in self.EXCLUDED_TERMS:
            if clean_text.startswith(term):
                return True
        return False
