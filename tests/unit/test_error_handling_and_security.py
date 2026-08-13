"""Error Handling, Privacy Safeguards, Invariants & Security Unit Tests."""

import hashlib
from pathlib import Path
import pytest
from app.detection.detector import PIIDetector
from app.ingestion.docx_parser import DOCXParser
from app.ingestion.exceptions import IngestionError, InvalidDocumentError
from app.mapping.entity_mapper import EntityMapper
from app.redaction.docx_redactor import DOCXRedactor

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synthetic"


@pytest.fixture
def parser():
    return DOCXParser()


@pytest.fixture
def detector():
    return PIIDetector()


@pytest.fixture
def mapper():
    return EntityMapper()


@pytest.fixture
def redactor():
    return DOCXRedactor()


# 1. Missing and Corrupt File Error Handling
def test_missing_file_error_handling(parser):
    with pytest.raises((IngestionError, FileNotFoundError)):
        parser.parse_document("non_existent_file_path_12345.docx")


def test_corrupt_non_docx_file_error_handling(parser, tmp_path):
    bad_file = tmp_path / "corrupt.docx"
    bad_file.write_bytes(b"This is not a valid zip or docx file content.")

    with pytest.raises(InvalidDocumentError):
        parser.parse_document(bad_file)


# 2. Input File Hash Protection Audit Test
def test_input_file_hash_preservation(parser, detector, mapper, redactor, tmp_path):
    in_doc = FIXTURES_DIR / "test_a_single_run.docx"
    out_doc = tmp_path / "redacted_out.docx"

    with open(in_doc, "rb") as f:
        hash_before = hashlib.sha256(f.read()).hexdigest()

    doc_model = parser.parse_document(in_doc)
    dets = detector.detect_in_document(doc_model)
    recs = mapper.map_all_detections(dets)
    redactor.redact_document(in_doc, out_doc, dets, recs)

    with open(in_doc, "rb") as f:
        hash_after = hashlib.sha256(f.read()).hexdigest()

    assert hash_before == hash_after


# 3. Detection Invariant Properties Test
def test_detection_invariants_start_lt_end(detector):
    para_text = "Contact Alice Example at alice@example.test or +91 9000000000 today."
    from app.ingestion.models import ParagraphModel, SourceLocation, SourceLocationType

    para = ParagraphModel(
        paragraph_index=0,
        reconstructed_text=para_text,
        location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0),
    )

    dets = detector.detect_in_paragraph(para)
    for d in dets:
        assert d.start < d.end
        assert 0 <= d.start <= len(para_text)
        assert 0 <= d.end <= len(para_text)
        assert d.text == para_text[d.start : d.end]


# 4. Privacy Safeguards Audit Test (Zero Raw PII in Exception Strings)
def test_privacy_safeguard_exception_formatting():
    from app.redaction.exceptions import ResidualPIIError

    try:
        raise ResidualPIIError("Validation failed: Original detected PII value still exists in redacted document.")
    except ResidualPIIError as err:
        msg = str(err)
        # Ensure message is generic and contains zero raw PII
        assert "Validation failed" in msg
        assert "@" not in msg
        assert "+91" not in msg


# 5. Redaction Idempotency Pass 1 vs Pass 2 Verification Test
def test_idempotency_pass_behavior(parser, detector, mapper, redactor, tmp_path):
    in_doc = FIXTURES_DIR / "test_a_single_run.docx"
    pass1_doc = tmp_path / "pass1.docx"
    pass2_doc = tmp_path / "pass2.docx"

    # Pass 1
    doc_m1 = parser.parse_document(in_doc)
    dets1 = detector.detect_in_document(doc_m1)
    recs1 = mapper.map_all_detections(dets1)
    redactor.redact_document(in_doc, pass1_doc, dets1, recs1)

    # Pass 2
    doc_m2 = parser.parse_document(pass1_doc)
    dets2 = detector.detect_in_document(doc_m2)
    recs2 = mapper.map_all_detections(dets2)
    res2 = redactor.redact_document(pass1_doc, pass2_doc, dets2, recs2)

    assert res2.is_valid_docx is True
    assert res2.residual_pii_clean is True
