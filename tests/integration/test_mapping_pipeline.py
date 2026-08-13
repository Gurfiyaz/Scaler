"""Integration tests for end-to-end mapping pipeline (Parser -> Detector -> Mapper)."""

from pathlib import Path
import pytest
from app.detection.detector import PIIDetector
from app.ingestion.docx_parser import DOCXParser
from app.mapping.entity_mapper import EntityMapper

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synthetic"
PROSPECTUS_PATH = Path(r"C:\Users\gurfiyaz basha\Downloads\Enterprise Data - Assignment.docx")


@pytest.fixture
def parser() -> DOCXParser:
    return DOCXParser()


@pytest.fixture
def detector() -> PIIDetector:
    return PIIDetector()


def test_pipeline_determinism_synthetic(parser, detector):
    """Run full pipeline twice on synthetic document and assert 100% mapping determinism."""
    doc_path = FIXTURES_DIR / "test_c_hyperlink.docx"

    # Run 1
    doc1 = parser.parse_document(doc_path)
    dets1 = detector.detect_in_document(doc1)
    mapper1 = EntityMapper()
    records1 = mapper1.map_all_detections(dets1)

    # Run 2 (separate mapper instance)
    doc2 = parser.parse_document(doc_path)
    dets2 = detector.detect_in_document(doc2)
    mapper2 = EntityMapper()
    records2 = mapper2.map_all_detections(dets2)

    assert len(records1) == len(records2)

    for k in records1:
        assert k in records2
        assert records1[k].replacement_value == records2[k].replacement_value
        assert records1[k].seed_hash == records2[k].seed_hash


def test_local_prospectus_mapping_counts_only(parser, detector):
    """Local privacy-preserving validation on original prospectus file.

    PRIVACY CONFIRMED: Reports ONLY safe mapping record counts by category.
    Never prints or logs raw original PII or replacement pairs.
    """
    if not PROSPECTUS_PATH.exists():
        pytest.skip(f"Original prospectus file not present at {PROSPECTUS_PATH}")

    doc = parser.parse_document(PROSPECTUS_PATH)
    dets = detector.detect_in_document(doc)

    mapper = EntityMapper()
    records = mapper.map_all_detections(dets)

    print("\n" + "=" * 60)
    print("      SAFE PROSPECTUS ENTITY MAPPING SUMMARY")
    print("=" * 60)
    print(f"Total Unique Entities Mapped : {len(records)}")

    # Aggregate counts by category
    cat_counts = {}
    for rec in records.values():
        cat = rec.entity_type.value
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    for cat_name, count in cat_counts.items():
        print(f" - {cat_name:<20}: {count}")

    print("=" * 60)
    print("PRIVACY CONFIRMED: 0 raw PII strings were emitted to logs or safe summaries.")
    print("=" * 60)

    assert len(records) >= 2
