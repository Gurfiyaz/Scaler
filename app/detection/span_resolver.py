"""Span Normalization and Overlap Resolution Engine."""

from typing import List
from app.detection.models import PIIDetection, PIIType


class SpanResolver:
    """Normalizes detection boundaries and resolves overlapping PII spans based on priority rules."""

    # Priority Rank (Lower integer = Higher priority)
    PRIORITY_RANK = {
        PIIType.EMAIL_ADDRESS: 1,
        PIIType.CREDIT_CARD: 2,
        PIIType.IP_ADDRESS: 3,
        PIIType.PHONE_NUMBER: 4,
        PIIType.SSN: 5,
        PIIType.DATE_OF_BIRTH: 6,
        PIIType.ADDRESS: 7,
        PIIType.ORGANIZATION: 8,
        PIIType.PERSON: 9,
    }

    @classmethod
    def normalize_detection(cls, det: PIIDetection, full_text: str) -> PIIDetection:
        """Strip surrounding punctuation, quotes, and colons, adjusting offsets accordingly."""
        text_span = det.text

        # Strip trailing colons, periods, commas, quotes, brackets
        r_stripped = text_span.rstrip(":,;.\"'()[]{}")
        r_trimmed_len = len(text_span) - len(r_stripped)

        l_stripped = r_stripped.lstrip("\"'()[]{} ")
        l_trimmed_len = len(r_stripped) - len(l_stripped)

        new_start = det.start + l_trimmed_len
        new_end = det.end - r_trimmed_len
        new_text = full_text[new_start:new_end] if 0 <= new_start <= new_end <= len(full_text) else l_stripped

        return PIIDetection(
            entity_type=det.entity_type,
            start=new_start,
            end=new_end,
            text=new_text,
            recognizer=det.recognizer,
            confidence=det.confidence,
            paragraph_index=det.paragraph_index,
            location=det.location,
            run_indices=det.run_indices,
            metadata=det.metadata,
        )

    @classmethod
    def resolve_overlaps(
        cls, detections: List[PIIDetection], paragraph_text: str
    ) -> List[PIIDetection]:
        """Resolve overlapping detection candidate spans deterministically.

        Priority Rules:
        1. Higher Category Priority (EMAIL > CREDIT_CARD > IP > PHONE > SSN > DOB > ADDRESS > ORG > PERSON).
        2. Higher Confidence Score.
        3. Longer Span Length (end - start).
        """
        if not detections:
            return []

        # 1. Normalize all detections
        normalized_dets = [cls.normalize_detection(d, paragraph_text) for d in detections]

        # Filter out empty or invalid spans
        valid_dets = [d for d in normalized_dets if d.end > d.start and d.text.strip()]

        # 2. Sort by: (1) Category Priority Ascending, (2) Confidence Descending, (3) Length Descending, (4) Start Offset Ascending
        def sort_key(d: PIIDetection):
            rank = cls.PRIORITY_RANK.get(d.entity_type, 99)
            length = d.end - d.start
            return (rank, -d.confidence, -length, d.start)

        sorted_candidates = sorted(valid_dets, key=sort_key)

        resolved: List[PIIDetection] = []

        for candidate in sorted_candidates:
            # Check overlap with already accepted detections
            has_overlap = False
            for accepted in resolved:
                # Half-open interval overlap check [start, end)
                if max(candidate.start, accepted.start) < min(candidate.end, accepted.end):
                    has_overlap = True
                    break

            if not has_overlap:
                resolved.append(candidate)

        # Final return sorted by start offset
        return sorted(resolved, key=lambda d: d.start)
