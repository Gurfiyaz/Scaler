"""Scalability and Determinism Unit Tests for EntityMapper (Phase 10.5)."""

import os
import subprocess
import sys
from pathlib import Path
import pytest

from app.detection.models import PIIDetection, PIIType
from app.ingestion.models import SourceLocation, SourceLocationType
from app.mapping.entity_mapper import EntityMapper
from app.mapping.exceptions import CollisionError


def test_3000_unique_organization_mappings_no_collision_error():
    """Verify that EntityMapper can map 3,000 unique organization entities without CollisionError."""
    mapper = EntityMapper()
    detections = []
    loc = SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0)

    for i in range(3000):
        org_text = f"Synthetic Enterprise Solutions_{i} Pvt Ltd"
        det = PIIDetection(
            entity_type=PIIType.ORGANIZATION,
            start=0,
            end=len(org_text),
            text=org_text,
            recognizer="regex",
            confidence=0.99,
            paragraph_index=0,
            location=loc,
        )
        detections.append(det)

    records = mapper.map_all_detections(detections)
    assert len(records) == 3000
    assert len(mapper._used_replacements) == 3000


def test_repeated_entity_consistency_2_100_1000_times():
    """Verify that the same normalized entity repeated N times produces 100% identical replacement."""
    mapper = EntityMapper()
    loc = SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0)
    org_text = "Acme Global Technology Corporation Pvt Ltd"

    dets = [
        PIIDetection(
            entity_type=PIIType.ORGANIZATION,
            start=0,
            end=len(org_text),
            text=org_text,
            recognizer="regex",
            confidence=0.99,
            paragraph_index=0,
            location=loc,
        )
        for _ in range(1000)
    ]

    records = mapper.map_all_detections(dets)
    # 1000 occurrences should produce exactly ONE unique mapping record
    assert len(records) == 1
    key = list(records.keys())[0]
    rec = records[key]
    assert rec.original_value == org_text


def test_category_scoped_uniqueness():
    """Verify that PERSON and ORGANIZATION with identical names do not collide."""
    mapper = EntityMapper()
    loc = SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0)

    det_person = PIIDetection(
        entity_type=PIIType.PERSON,
        start=0,
        end=19,
        text="Apollo Technologies",
        recognizer="ner",
        confidence=0.95,
        paragraph_index=0,
        location=loc,
    )

    det_org = PIIDetection(
        entity_type=PIIType.ORGANIZATION,
        start=0,
        end=19,
        text="Apollo Technologies",
        recognizer="regex",
        confidence=0.95,
        paragraph_index=0,
        location=loc,
    )

    rec_person = mapper.map_detection(det_person)
    rec_org = mapper.map_detection(det_org)

    assert rec_person.entity_type == PIIType.PERSON
    assert rec_org.entity_type == PIIType.ORGANIZATION
    assert rec_person.replacement_value != rec_org.replacement_value


def test_cross_process_determinism():
    """Verify that EntityMapper produces identical fingerprints across separate Python processes."""
    code = """
import sys
from pathlib import Path
sys.path.insert(0, r'{}')
from app.detection.models import PIIDetection, PIIType
from app.ingestion.models import SourceLocation, SourceLocationType
from app.mapping.entity_mapper import EntityMapper

mapper = EntityMapper()
loc = SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0)
det = PIIDetection(
    entity_type=PIIType.ORGANIZATION,
    start=0,
    end=32,
    text="CrossProcess Test Entity Pvt Ltd",
    recognizer="regex",
    confidence=0.99,
    paragraph_index=0,
    location=loc,
)
rec = mapper.map_detection(det)
print(f"HASH:{{rec.seed_hash}}|VAL:{{rec.replacement_value}}")
""".format(
        str(Path(__file__).parent.parent.parent).replace("\\", "\\\\")
    )

    p1 = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    p2 = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)

    out1 = p1.stdout.strip()
    out2 = p2.stdout.strip()

    assert out1 == out2
    assert "HASH:" in out1
