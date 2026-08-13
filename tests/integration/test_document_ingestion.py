"""Integration tests for document ingestion against synthetic DOCX test fixtures."""

from pathlib import Path
import pytest
from app.ingestion.docx_parser import DOCXParser

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synthetic"


@pytest.fixture
def parser() -> DOCXParser:
    """Fixture providing DOCXParser instance."""
    return DOCXParser()


def test_integration_single_run(parser):
    """Test A: Ingestion of single-run paragraph document."""
    doc_path = FIXTURES_DIR / "test_a_single_run.docx"
    doc_model = parser.parse_document(doc_path)

    assert len(doc_model.paragraphs) == 1
    p0 = doc_model.paragraphs[0]
    assert "Alice Example" in p0.reconstructed_text
    assert len(p0.runs) == 1
    assert p0.runs[0].start_offset == 0
    assert p0.runs[0].end_offset == len(p0.reconstructed_text)


def test_integration_split_run(parser):
    """Test B: Ingestion of split-run paragraph document ('Alice ' + 'Example')."""
    doc_path = FIXTURES_DIR / "test_b_split_run.docx"
    doc_model = parser.parse_document(doc_path)

    assert len(doc_model.paragraphs) == 1
    p0 = doc_model.paragraphs[0]
    assert p0.reconstructed_text == "Alice Example"
    assert len(p0.runs) == 2
    assert p0.runs[0].text == "Alice "
    assert p0.runs[0].start_offset == 0
    assert p0.runs[0].end_offset == 6
    assert p0.runs[1].text == "Example"
    assert p0.runs[1].start_offset == 6
    assert p0.runs[1].end_offset == 13


def test_integration_hyperlink_relationship(parser):
    """Test C: Hyperlink extraction and relationship target resolution."""
    doc_path = FIXTURES_DIR / "test_c_hyperlink.docx"
    doc_model = parser.parse_document(doc_path)

    assert len(doc_model.hyperlinks) == 1
    link = doc_model.hyperlinks[0]
    assert link.display_text == "alice@example.test"
    assert link.target_uri == "mailto:alice@example.test"
    assert link.target_mode == "External"


def test_integration_table_extraction(parser):
    """Test D: Extraction of tables, rows, cells, and cell paragraphs."""
    doc_path = FIXTURES_DIR / "test_d_table.docx"
    doc_model = parser.parse_document(doc_path)

    assert len(doc_model.tables) == 1
    tbl = doc_model.tables[0]
    assert len(tbl.rows) == 2
    assert len(tbl.rows[0].cells) == 2

    # Check cell content
    c00 = tbl.rows[0].cells[0].paragraphs[0]
    c10 = tbl.rows[1].cells[0].paragraphs[0]
    assert c00.reconstructed_text == "Employee Name"
    assert c10.reconstructed_text == "Alice Example"
    assert c10.location.location_type.value == "table"
    assert c10.location.table_index == 0
    assert c10.location.row_index == 1
    assert c10.location.cell_index == 0


def test_integration_header_footer(parser):
    """Test E: Header and footer extraction."""
    doc_path = FIXTURES_DIR / "test_e_header_footer.docx"
    doc_model = parser.parse_document(doc_path)

    assert len(doc_model.headers) >= 1
    assert len(doc_model.footers) >= 1

    hdr_text = doc_model.headers[0].paragraphs[0].reconstructed_text
    ftr_text = doc_model.footers[0].paragraphs[0].reconstructed_text

    assert "Header" in hdr_text
    assert "Footer" in ftr_text
    assert doc_model.headers[0].paragraphs[0].location.location_type.value == "header"
    assert doc_model.footers[0].paragraphs[0].location.location_type.value == "footer"


def test_integration_formatting_metadata(parser):
    """Test F: Extraction of bold, italic, underline, and color metadata."""
    doc_path = FIXTURES_DIR / "test_f_formatting.docx"
    doc_model = parser.parse_document(doc_path)

    p0 = doc_model.paragraphs[0]
    assert len(p0.runs) == 4

    assert p0.runs[0].formatting.bold is True
    assert p0.runs[1].formatting.italic is True
    assert p0.runs[2].formatting.underline is True
    assert p0.runs[3].formatting.color_hex is not None
