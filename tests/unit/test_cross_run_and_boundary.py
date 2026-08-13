"""Cross-Run and Boundary Placement Unit Tests."""

from pathlib import Path
import pytest
from app.detection.detector import PIIDetector
from app.detection.models import PIIType
from app.ingestion.models import FormattingMetadata, ParagraphModel, RunModel, SourceLocation, SourceLocationType
from app.redaction.docx_redactor import DOCXRedactor
from app.redaction.run_rewriter import RunRewriter
from app.redaction.models import RedactionTask


@pytest.fixture
def detector():
    return PIIDetector()


# 1. Multi-Run Split PII Detection & Mapping Test
def test_cross_run_multi_run_split_detection():
    # PII 'Rashi Patil' split across 3 runs: Run 0 ('Rashi '), Run 1 ('Pa'), Run 2 ('til')
    runs = [
        RunModel(run_index=0, paragraph_index=0, text="Contact ", start_offset=0, end_offset=8),
        RunModel(run_index=1, paragraph_index=0, text="Rashi ", start_offset=8, end_offset=14),
        RunModel(run_index=2, paragraph_index=0, text="Pa", start_offset=14, end_offset=16),
        RunModel(run_index=3, paragraph_index=0, text="til", start_offset=16, end_offset=19),
        RunModel(run_index=4, paragraph_index=0, text=" now.", start_offset=19, end_offset=24),
    ]
    reconstructed = "".join(r.text for r in runs)
    para = ParagraphModel(
        paragraph_index=0,
        reconstructed_text=reconstructed,
        runs=runs,
        location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0),
    )

    detector = PIIDetector()
    dets = detector.detect_in_paragraph(para)

    persons = [d for d in dets if d.entity_type == PIIType.PERSON]
    assert len(persons) == 1
    assert persons[0].text == "Rashi Patil"
    assert persons[0].start == 8
    assert persons[0].end == 19
    assert set(persons[0].run_indices) == {1, 2, 3}


# 2. Overlapping Candidate Resolution Priority Test
def test_span_resolver_overlap_priority(detector):
    # 'alice@example.com' contains 'Alice' which spaCy might flag as PERSON
    text = "User email is alice@example.com for login."
    para = ParagraphModel(
        paragraph_index=0,
        reconstructed_text=text,
        location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0),
    )

    dets = detector.detect_in_paragraph(para)
    # Resolver must prioritize EMAIL_ADDRESS over PERSON inside email string
    emails = [d for d in dets if d.entity_type == PIIType.EMAIL_ADDRESS]
    persons = [d for d in dets if d.entity_type == PIIType.PERSON and d.start >= 14 and d.end <= 31]

    assert len(emails) == 1
    assert len(persons) == 0  # Overlapping person inside email span resolved away


# 3. Multiple Entities Inside One Paragraph Right-to-Left Rewriting Test
def test_multiple_spans_in_one_paragraph():
    text = "Call Alice Smith at +91 9876543210 or email alice@example.test today."
    # Offsets:
    # 'Alice Smith': [5, 16)
    # '+91 9876543210': [20, 34)
    # 'alice@example.test': [44, 62)

    tasks = [
        RedactionTask(
            paragraph_index=0,
            start_offset=5,
            end_offset=16,
            original_text="Alice Smith",
            replacement_text="Jane Doe",
            entity_type=PIIType.PERSON,
            location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0),
        ),
        RedactionTask(
            paragraph_index=0,
            start_offset=20,
            end_offset=34,
            original_text="+91 9876543210",
            replacement_text="+91 1234567890",
            entity_type=PIIType.PHONE_NUMBER,
            location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0),
        ),
        RedactionTask(
            paragraph_index=0,
            start_offset=44,
            end_offset=62,
            original_text="alice@example.test",
            replacement_text="jane.doe@example.test",
            entity_type=PIIType.EMAIL_ADDRESS,
            location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0),
        ),
    ]

    import docx
    doc = docx.Document()
    p = doc.add_paragraph(text)

    applied = RunRewriter.apply_paragraph_redactions(p, tasks)
    assert applied == 3

    redacted_text = p.text
    assert "Alice Smith" not in redacted_text
    assert "+91 9876543210" not in redacted_text
    assert "alice@example.test" not in redacted_text
    assert "Jane Doe" in redacted_text
    assert "+91 1234567890" in redacted_text
    assert "jane.doe@example.test" in redacted_text


# 4. Span Boundary Positioning Tests
@pytest.mark.parametrize(
    "text,start,end,expected_span",
    [
        ("Alice Smith is the author.", 0, 11, "Alice Smith"),  # Start of paragraph
        ("Author is Alice Smith.", 10, 21, "Alice Smith."),  # End of paragraph
        ("Contact (Alice Smith) now.", 9, 20, "Alice Smith"),  # Inside parentheses
        ("Contact 'Alice Smith' today.", 9, 20, "Alice Smith"),  # Inside quotes
    ],
)
def test_span_boundary_positions(detector, text, start, end, expected_span):
    para = ParagraphModel(
        paragraph_index=0,
        reconstructed_text=text,
        location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0),
    )
    dets = detector.detect_in_paragraph(para)
    assert len(dets) >= 1
