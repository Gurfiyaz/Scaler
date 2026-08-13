"""Entity Mapping and Cross-Entity Association Unit Tests."""

import subprocess
import sys
import pytest
from app.detection.models import PIIDetection, PIIType
from app.mapping.entity_mapper import EntityMapper
from app.ingestion.models import SourceLocation, SourceLocationType


@pytest.fixture
def mapper():
    return EntityMapper()


def make_det(cat: PIIType, text: str, idx: int = 0) -> PIIDetection:
    return PIIDetection(
        entity_type=cat,
        start=0,
        end=len(text),
        text=text,
        recognizer="test",
        confidence=1.0,
        paragraph_index=idx,
        location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=idx),
    )


# 1. Determinism Across Separate Subprocesses Test
def test_subprocess_mapping_determinism():
    cmd = [
        sys.executable,
        "-c",
        "from app.mapping.entity_mapper import EntityMapper; "
        "from app.detection.models import PIIDetection, PIIType; "
        "m = EntityMapper(); "
        "d = PIIDetection(entity_type=PIIType.PERSON, start=0, end=9, text='Rohan Dey', recognizer='t', confidence=1.0, paragraph_index=0); "
        "recs = m.map_all_detections([d]); "
        "print(list(recs.values())[0].replacement_value)",
    ]

    out1 = subprocess.check_output(cmd, text=True, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL).strip().splitlines()[-1]
    out2 = subprocess.check_output(cmd, text=True, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL).strip().splitlines()[-1]

    assert out1 == out2
    assert len(out1) > 0


# 2. Case and Whitespace Normalization Consistency Test
def test_normalization_consistency_variations(mapper):
    d1 = make_det(PIIType.PERSON, "Rohan Dey")
    d2 = make_det(PIIType.PERSON, "  rohan   dey  ")

    recs1 = mapper.map_all_detections([d1])
    recs2 = mapper.map_all_detections([d2])

    val1 = list(recs1.values())[0].replacement_value
    val2 = list(recs2.values())[0].replacement_value

    assert val1 == val2


# 3. Person-Email Association vs Unlinked Generic Support Email Test
def test_person_email_linking_vs_unlinked(mapper):
    # Rohan Dey linked with rohan.dey@gmail.com
    person_det = make_det(PIIType.PERSON, "Rohan Dey", idx=5)
    email_det = make_det(PIIType.EMAIL_ADDRESS, "rohan.dey@gmail.com", idx=6)
    # Generic support email (unlinked to any person in document)
    support_det = make_det(PIIType.EMAIL_ADDRESS, "support@example.com", idx=10)

    recs = mapper.map_all_detections([person_det, email_det, support_det])

    person_rec = next(r for r in recs.values() if r.entity_type == PIIType.PERSON)
    email_rec = next(r for r in recs.values() if r.normalized_original == "rohan.dey@gmail.com")
    support_rec = next(r for r in recs.values() if r.normalized_original == "support@example.com")

    person_first = person_rec.replacement_value.split()[0].lower()
    person_last = person_rec.replacement_value.split()[-1].lower()

    # Linked email local part should contain person's synthetic name
    assert person_first in email_rec.replacement_value.lower() or person_last in email_rec.replacement_value.lower()

    # Unlinked support email should receive valid deterministic email replacement
    assert len(support_rec.replacement_value) > 0
    assert "@" in support_rec.replacement_value


# 4. Replacement Safety Rejection Test
def test_replacement_safety_rejection(mapper):
    d1 = make_det(PIIType.PERSON, "Rashi Patil")
    recs = mapper.map_all_detections([d1])
    rec = list(recs.values())[0]

    # Replacement value must not match original value
    assert rec.replacement_value != "Rashi Patil"
    # Replacement value must be non-empty
    assert len(rec.replacement_value.strip()) > 0
