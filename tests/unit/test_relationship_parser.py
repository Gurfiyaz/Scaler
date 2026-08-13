"""Unit tests for RelationshipParser XML module."""

import io
import zipfile
import pytest
from app.ingestion.relationship_parser import RelationshipParser


def test_parse_relationships_valid_xml():
    """Test extracting relationship records from synthetic .rels XML string."""
    rels_xml = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        b'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="mailto:test@example.com" TargetMode="External"/>'
        b'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        b'</Relationships>'
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/_rels/document.xml.rels", rels_xml)

    buf.seek(0)
    with zipfile.ZipFile(buf, "r") as z:
        rels = RelationshipParser.parse_relationships_from_zip(z, "word/_rels/document.xml.rels")

    assert len(rels) == 2
    assert "rId1" in rels
    assert rels["rId1"].target == "mailto:test@example.com"
    assert rels["rId1"].target_mode == "External"
    assert "rId2" in rels
    assert rels["rId2"].target == "styles.xml"


def test_parse_relationships_missing_rels_file():
    """Test graceful handling when .rels file does not exist in zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("dummy.txt", "hello")

    buf.seek(0)
    with zipfile.ZipFile(buf, "r") as z:
        rels = RelationshipParser.parse_relationships_from_zip(z, "missing.xml.rels")

    assert rels == {}
