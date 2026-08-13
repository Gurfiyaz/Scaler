"""End-to-End API Pipeline Integration Tests."""

import hashlib
import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.ingestion.docx_parser import DOCXParser
from app.main import app

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synthetic"
client = TestClient(app)


def test_full_api_redaction_pipeline_synthetic(tmp_path):
    fixture_path = FIXTURES_DIR / "test_d_table.docx"
    with open(fixture_path, "rb") as f:
        file_bytes = f.read()
    hash_before = hashlib.sha256(file_bytes).hexdigest()

    # 1. Upload & Process
    res = client.post(
        "/api/process",
        files={"file": ("test_d_table.docx", io.BytesIO(file_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "completed"
    assert data["total_detections"] == 3
    assert data["replacements_applied"] == 3
    assert data["validation"]["document_valid"] is True
    assert data["validation"]["original_pii_residual_check"] is True
    assert data["validation"]["original_file_hash_unchanged"] is True

    download_id = data["download_id"]

    # 2. Download Redacted File
    dl_res = client.get(f"/api/download/{download_id}")
    assert dl_res.status_code == 200

    out_file = tmp_path / "downloaded_redacted.docx"
    out_file.write_bytes(dl_res.content)

    # 3. Inspect Downloaded DOCX Structure & Content
    parser = DOCXParser()
    redacted_model = parser.parse_document(out_file)

    full_text = " ".join(p.reconstructed_text for p in redacted_model.paragraphs)
    for table in redacted_model.tables:
        for row in table.rows:
            for cell in row.cells:
                full_text += " " + " ".join(p.reconstructed_text for p in cell.paragraphs)

    assert "Alice Example" not in full_text
    assert "+91 9000000000" not in full_text

    # 4. Verify Original Input File Hash Hash Protection
    hash_after = hashlib.sha256(file_bytes).hexdigest()
    assert hash_before == hash_after
