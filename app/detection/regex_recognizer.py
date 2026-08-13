"""Deterministic Regex Recognizer for structured PII types."""

import re
from typing import List
from app.detection.models import PIIDetection, PIIType
from app.detection.validators import validate_ip, validate_luhn, validate_phone, validate_ssn
from app.ingestion.models import ParagraphModel


class RegexRecognizer:
    """Detects EMAIL, PHONE, IP, CREDIT_CARD, and SSN using regex and checksum validators."""

    # Robust RFC 5322 compliant Email Regex
    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )

    # Candidate Phone Pattern: International / Indian (+91 98765 43210, +91-9876543210, 9876543210)
    PHONE_PATTERN = re.compile(
        r"(?:\+?\d{1,3}[\s-]?)?\(?\d{2,5}\)?[\s-]?\d{3,5}[\s-]?\d{3,5}\b"
    )

    # Candidate IP Pattern (IPv4 & IPv6 candidate format including compressed ::)
    IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    IPV6_PATTERN = re.compile(r"(?<![0-9a-fA-F:])(?:[0-9a-fA-F]{1,4}:){1,7}[0-9a-fA-F]{1,4}(?![0-9a-fA-F:])|(?<![0-9a-fA-F:])(?:[0-9a-fA-F]{1,4}:)*::?(?:[0-9a-fA-F]{1,4}:)*[0-9a-fA-F]{1,4}(?![0-9a-fA-F:])")

    # Candidate Credit Card Pattern (13-19 digits with optional spaces or hyphens)
    CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

    # Strict US SSN Pattern (XXX-XX-XXXX)
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

    def detect_in_paragraph(self, paragraph: ParagraphModel) -> List[PIIDetection]:
        """Run all regex recognizers on a paragraph and return validated PIIDetection objects."""
        text = paragraph.reconstructed_text
        p_idx = paragraph.paragraph_index
        loc = paragraph.location

        detections: List[PIIDetection] = []

        # 1. Email Detection
        for match in self.EMAIL_PATTERN.finditer(text):
            val = match.group(0).strip()
            # Strip trailing punctuation if accidentally matched
            val = val.rstrip(".:,;")
            start = match.start()
            end = start + len(val)

            detections.append(
                PIIDetection(
                    entity_type=PIIType.EMAIL_ADDRESS,
                    start=start,
                    end=end,
                    text=val,
                    recognizer="regex_email",
                    confidence=1.0,
                    paragraph_index=p_idx,
                    location=loc,
                )
            )

        # 2. Phone Number Detection
        for match in self.PHONE_PATTERN.finditer(text):
            val = match.group(0).strip()
            # Must pass Google libphonenumber validation
            if validate_phone(val):
                start = match.start()
                end = match.end()
                detections.append(
                    PIIDetection(
                        entity_type=PIIType.PHONE_NUMBER,
                        start=start,
                        end=end,
                        text=val,
                        recognizer="regex_phone",
                        confidence=0.95,
                        paragraph_index=p_idx,
                        location=loc,
                    )
                )

        # 3. IP Address Detection
        for pattern in (self.IPV4_PATTERN, self.IPV6_PATTERN):
            for match in pattern.finditer(text):
                val = match.group(0).strip().rstrip(".:,;")
                start = match.start()
                end = start + len(val)

                # Exclude version strings such as "version 1.2.3.4" or "v1.2.3.4"
                prefix = text[max(0, start - 10) : start].lower()
                if "version" in prefix or prefix.endswith("v") or prefix.endswith("v."):
                    continue

                if validate_ip(val):
                    detections.append(
                        PIIDetection(
                            entity_type=PIIType.IP_ADDRESS,
                            start=start,
                            end=end,
                            text=val,
                            recognizer="regex_ip",
                            confidence=1.0,
                            paragraph_index=p_idx,
                            location=loc,
                        )
                    )

        # 4. Credit Card Detection
        for match in self.CREDIT_CARD_PATTERN.finditer(text):
            val = match.group(0).strip()
            # Must pass Luhn checksum validation
            if validate_luhn(val):
                start = match.start()
                end = match.end()
                detections.append(
                    PIIDetection(
                        entity_type=PIIType.CREDIT_CARD,
                        start=start,
                        end=end,
                        text=val,
                        recognizer="luhn_credit_card",
                        confidence=1.0,
                        paragraph_index=p_idx,
                        location=loc,
                    )
                )

        # 5. Strict US SSN Detection
        for match in self.SSN_PATTERN.finditer(text):
            val = match.group(0).strip()
            if validate_ssn(val):
                start = match.start()
                end = match.end()
                detections.append(
                    PIIDetection(
                        entity_type=PIIType.SSN,
                        start=start,
                        end=end,
                        text=val,
                        recognizer="regex_ssn",
                        confidence=1.0,
                        paragraph_index=p_idx,
                        location=loc,
                    )
                )

        return detections
