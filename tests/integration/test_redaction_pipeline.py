"""Integration tests for end-to-end redaction pipeline (Parser -> Detector -> Mapper -> Redactor -> Validator)."""

import time
from pathlib import Path
import pytest

from app.detection.detector import PIIDetector
from app.ingestion.docx_parser import DOCXParser
from app.mapping.entity_mapper import EntityMapper
from app.redaction.docx_redactor import DOCXRedactor

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synthetic"
PROSPECTUS_PATH = Path(r"C:\Users\gurfiyaz basha\Downloads\Enterprise Data - Assignment.docx")


@pytest.fixture
def parser() -> DOCXParser:
    return DOCXParser()


@pytest.fixture
def detector() -> PIIDetector:
    return PIIDetector()


@pytest.fixture
def mapper() -> EntityMapper:
    return EntityMapper()


@pytest.fixture
def redactor() -> DOCXRedactor:
    return DOCXRedactor()


def test_pipeline_all_synthetic_fixtures(parser, detector, mapper, redactor, tmp_path):
    """Run full redaction pipeline across all 9 synthetic test fixtures."""
    fixture_files = list(FIXTURES_DIR.glob("*.docx"))
    assert len(fixture_files) >= 9

    for fix_file in fixture_files:
        output_file = tmp_path / f"redacted_{fix_file.name}"

        doc_model = parser.parse_document(fix_file)
        dets = detector.detect_in_document(doc_model)
        records = mapper.map_all_detections(dets)

        result = redactor.redact_document(fix_file, output_file, dets, records)

        assert result.is_valid_docx is True
        assert result.residual_pii_clean is True
        assert output_file.exists()


def test_local_prospectus_redaction_pipeline(parser, detector, mapper, redactor, tmp_path):
    """Local privacy-preserving validation on original prospectus file.

    CRITICAL SAFETY RULE: Never modifies input prospectus. Writes output to separate redacted_prospectus.docx.
    PRIVACY CONFIRMED: Reports ONLY safe counts and timing metrics. Never prints raw PII.
    """
    if not PROSPECTUS_PATH.exists():
        pytest.skip(f"Original prospectus file not present at {PROSPECTUS_PATH}")

    output_path = tmp_path / "redacted_prospectus.docx"

    initial_hash = DOCXRedactor.calculate_file_hash(PROSPECTUS_PATH)

    t0 = time.perf_counter()
    doc = parser.parse_document(PROSPECTUS_PATH)
    t_parse = time.perf_counter() - t0

    t1 = time.perf_counter()
    dets = detector.detect_in_document(doc)
    t_detect = time.perf_counter() - t1

    t2 = time.perf_counter()
    records = mapper.map_all_detections(dets)
    t_map = time.perf_counter() - t2

    t3 = time.perf_counter()
    result = redactor.redact_document(PROSPECTUS_PATH, output_path, dets, records)
    t_redact = time.perf_counter() - t3

    final_hash = DOCXRedactor.calculate_file_hash(PROSPECTUS_PATH)

    # 1. Protection verification
    assert initial_hash == final_hash

    # 2. Structural & Residual PII verification
    assert result.is_valid_docx is True
    assert result.residual_pii_clean is True
    assert result.replacements_applied >= 10

    total_time = t_parse + t_detect + t_map + t_redact

    print("\n" + "=" * 60)
    print("      SAFE PROSPECTUS REDACTION PIPELINE SUMMARY")
    print("=" * 60)
    print(f"Total Detections Found       : {len(dets)}")
    print(f"Unique Entities Mapped       : {len(records)}")
    print(f"Replacements Applied         : {result.replacements_applied}")
    print(f"Output Document Valid        : YES ({result.is_valid_docx})")
    print(f"Original PII Residual Check : PASS ({result.residual_pii_clean})")
    print(f"Original File Hash Unchanged : YES (Verified)")
    print("-" * 60)
    print(f"Parsing Time                 : {t_parse * 1000:.2f} ms")
    print(f"Detection Time               : {t_detect * 1000:.2f} ms")
    print(f"Mapping Time                 : {t_map * 1000:.2f} ms")
    print(f"Redaction & Validation Time  : {t_redact * 1000:.2f} ms")
    print(f"Total Combined Pipeline Time : {total_time * 1000:.2f} ms ({total_time:.4f} s)")
    print("=" * 60)
    print("PRIVACY CONFIRMED: 0 raw PII strings were emitted to logs or safe summaries.")
    print("=" * 60)
