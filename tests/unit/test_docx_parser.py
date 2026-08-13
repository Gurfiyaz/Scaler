"""Unit tests for DOCXParser exception handling and validation."""

import io
import zipfile
import pytest
from app.ingestion.docx_parser import DOCXParser
from app.ingestion.exceptions import (
    CorruptedDocumentError,
    DocumentNotFoundError,
    EmptyDocumentError,
    InvalidDocumentError,
)


def test_parser_missing_file():
    """Test that non-existent file path raises DocumentNotFoundError."""
    parser = DOCXParser()
    with pytest.raises(DocumentNotFoundError):
        parser.parse_document("non_existent_file_path_12345.docx")


def test_parser_non_zip_file(tmp_path):
    """Test that a non-ZIP file raises InvalidDocumentError."""
    bad_file = tmp_path / "bad.docx"
    bad_file.write_text("This is not a zip file.")

    parser = DOCXParser()
    with pytest.raises(InvalidDocumentError):
        parser.parse_document(bad_file)


def test_parser_zip_missing_document_xml(tmp_path):
    """Test that a ZIP container missing word/document.xml raises InvalidDocumentError."""
    bad_zip = tmp_path / "no_doc.docx"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("dummy.txt", "hello")

    bad_zip.write_bytes(buf.getvalue())

    parser = DOCXParser()
    with pytest.raises(InvalidDocumentError):
        parser.parse_document(bad_zip)
