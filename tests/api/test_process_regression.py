"""Regression test for API process and download lifecycle non-blocking execution."""

import io
from pathlib import Path
import docx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synthetic"


def test_api_process_and_download_flow_regression():
    """Verify POST /api/process returns 200 and GET /api/download/{download_id} retrieves valid DOCX."""
    fixture_path = FIXTURES_DIR / "test_g_multiple_spans.docx"
    with open(fixture_path, "rb") as f:
        file_bytes = f.read()

    # 1. Process Upload
    response = client.post(
        "/api/process",
        files={
            "file": (
                "pii_redaction_test.docx",
                io.BytesIO(file_bytes),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    assert data["status"] == "completed"
    assert data["filename"] == "redacted_pii_redaction_test.docx"
    assert data["total_detections"] > 0
    assert data["replacements_applied"] > 0
    assert data["validation"]["document_valid"] is True
    assert data["validation"]["original_pii_residual_check"] is True
    assert data["validation"]["original_file_hash_unchanged"] is True

    download_id = data["download_id"]
    assert len(download_id) == 36

    # 2. Download Redacted File
    download_res = client.get(f"/api/download/{download_id}")
    assert download_res.status_code == 200
    assert (
        download_res.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    # 3. Verify Downloaded DOCX Integrity
    downloaded_bytes = download_res.content
    assert downloaded_bytes.startswith(b"PK\x03\x04")

    downloaded_doc = docx.Document(io.BytesIO(downloaded_bytes))
    assert len(downloaded_doc.paragraphs) > 0

    # Privacy Check: Raw PII must NOT appear in JSON response
    json_text = response.text
    for pii_val in ["alice@example.com", "9876543210", "192.0.2.1"]:
        assert pii_val not in json_text
