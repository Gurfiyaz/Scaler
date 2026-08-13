"""API Document Upload and Processing Endpoint Tests."""

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synthetic"
client = TestClient(app)


def test_process_valid_docx_upload():
    fixture_path = FIXTURES_DIR / "test_a_single_run.docx"
    with open(fixture_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/process",
        files={"file": ("test_a_single_run.docx", io.BytesIO(file_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    assert data["filename"] == "redacted_test_a_single_run.docx"
    assert data["total_detections"] == 1
    assert data["replacements_applied"] == 1
    assert data["validation"]["document_valid"] is True
    assert data["validation"]["original_pii_residual_check"] is True
    assert data["validation"]["original_file_hash_unchanged"] is True
    assert len(data["download_id"]) == 36

    # Privacy Audit: Confirm zero raw PII strings in JSON payload
    json_str = response.text
    assert "Alice Example" not in json_str
    assert "alice@example.com" not in json_str


def test_reject_non_docx_txt_file():
    txt_content = b"This is plain text with email john@example.com"
    response = client.post(
        "/api/process",
        files={"file": ("document.txt", io.BytesIO(txt_content), "text/plain")},
    )
    assert response.status_code == 400
    data = response.json()
    # Accept flat {"error": ...} or nested {"detail": {"error": ...}} format
    err = data.get("error") or (data.get("detail") or {}).get("error", "")
    assert "Invalid document" in err or response.status_code == 400


def test_reject_non_docx_renamed_pdf():
    pdf_content = b"%PDF-1.4 Fake PDF header content"
    response = client.post(
        "/api/process",
        files={"file": ("fake_doc.docx", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert response.status_code == 400
    data = response.json()
    # Accept flat {"message": ...} or nested {"detail": {"message": ...}} format
    msg = data.get("message") or (data.get("detail") or {}).get("message", "")
    assert "not a valid DOCX container" in msg or response.status_code == 400


def test_reject_corrupt_docx_zip():
    bad_zip = b"PK\x03\x04Corrupted zip content missing document.xml"
    response = client.post(
        "/api/process",
        files={"file": ("corrupt.docx", io.BytesIO(bad_zip), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400


def test_reject_empty_file():
    response = client.post(
        "/api/process",
        files={"file": ("empty.docx", io.BytesIO(b""), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert response.status_code == 400


def test_security_headers_present():
    response = client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
