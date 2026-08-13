"""Unit tests for RunMapper cross-run span mapping utility."""

import pytest
from app.ingestion.models import FormattingMetadata, ParagraphModel, RunModel, SourceLocation, SourceLocationType
from app.ingestion.run_mapper import RunMapper


@pytest.fixture
def sample_split_paragraph() -> ParagraphModel:
    """Fixture returning a paragraph split across 3 runs.

    Text: "Contact Rohan Dey today"
    Run 0: "Contact " (offsets 0..8)
    Run 1: "Rohan "   (offsets 8..14)
    Run 2: "Dey today" (offsets 14..23)
    """
    runs = [
        RunModel(run_index=0, paragraph_index=0, text="Contact ", start_offset=0, end_offset=8),
        RunModel(run_index=1, paragraph_index=0, text="Rohan ", start_offset=8, end_offset=14),
        RunModel(run_index=2, paragraph_index=0, text="Dey today", start_offset=14, end_offset=23),
    ]
    return ParagraphModel(
        paragraph_index=0,
        reconstructed_text="Contact Rohan Dey today",
        runs=runs,
        location=SourceLocation(location_type=SourceLocationType.BODY, paragraph_index=0),
    )


def test_span_entirely_within_one_run(sample_split_paragraph):
    """Test span contained completely inside Run 0 ('Contact')."""
    # Span for "Contact" -> 0..7
    runs = RunMapper.map_span_to_runs(sample_split_paragraph, 0, 7)
    assert len(runs) == 1
    assert runs[0].run_index == 0


def test_span_spanning_two_runs(sample_split_paragraph):
    """Test PII span ('Rohan Dey') spanning Run 1 and Run 2."""
    # "Rohan Dey" starts at index 8 and ends at index 17
    runs = RunMapper.map_span_to_runs(sample_split_paragraph, 8, 17)
    assert len(runs) == 2
    assert runs[0].run_index == 1
    assert runs[1].run_index == 2


def test_span_spanning_all_runs(sample_split_paragraph):
    """Test span covering text across all 3 runs."""
    runs = RunMapper.map_span_to_runs(sample_split_paragraph, 0, 23)
    assert len(runs) == 3
    assert [r.run_index for r in runs] == [0, 1, 2]


def test_span_at_beginning(sample_split_paragraph):
    """Test span at the start boundary of the paragraph."""
    runs = RunMapper.map_span_to_runs(sample_split_paragraph, 0, 3)
    assert len(runs) == 1
    assert runs[0].run_index == 0


def test_span_at_end(sample_split_paragraph):
    """Test span at the end boundary of the paragraph."""
    runs = RunMapper.map_span_to_runs(sample_split_paragraph, 18, 23)
    assert len(runs) == 1
    assert runs[0].run_index == 2


def test_empty_span(sample_split_paragraph):
    """Test zero-length span (start == end)."""
    runs = RunMapper.map_span_to_runs(sample_split_paragraph, 8, 8)
    assert len(runs) == 1
    assert runs[0].run_index == 1


def test_invalid_offsets_negative(sample_split_paragraph):
    """Test that negative offsets raise ValueError."""
    with pytest.raises(ValueError):
        RunMapper.map_span_to_runs(sample_split_paragraph, -1, 5)


def test_invalid_offsets_start_greater_than_end(sample_split_paragraph):
    """Test that start > end raises ValueError."""
    with pytest.raises(ValueError):
        RunMapper.map_span_to_runs(sample_split_paragraph, 10, 5)


def test_invalid_offsets_exceeding_length(sample_split_paragraph):
    """Test that end_offset exceeding text length raises ValueError."""
    with pytest.raises(ValueError):
        RunMapper.map_span_to_runs(sample_split_paragraph, 0, 100)
