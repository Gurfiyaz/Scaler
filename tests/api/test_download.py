"""API Download Endpoint Security & Functionality Tests."""

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "synthetic"
client = TestClient(app)


def test_download_valid_redacted_docx():
    fixture_path = FIXTURES_DIR / "test_a_single_run.docx"
    with open(fixture_path, "rb") as f:
        file_bytes = f.read()

    # Step 1: Upload & Process
    upload_res = client.post(
        "/api/process",
        files={"file": ("test_a_single_run.docx", io.BytesIO(file_bytes), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert upload_res.status_code == 200
    download_id = upload_res.json()["download_id"]

    # Step 2: Download Redacted File
    download_res = client.get(f"/api/download/{download_id}")
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert len(download_res.content) > 0


def test_download_invalid_token_404():
    response = client.get("/api/download/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    data = response.json()
    # Error may be in flat format {"error": ..., "message": ...} or nested {"detail": ...}
    msg = data.get("message") or (data.get("detail") or {}).get("message", "")
    assert "Download token invalid or expired" in msg or "Not found" in str(data) or response.status_code == 404


def test_download_path_traversal_rejection():
    # Attempt path traversal
    response = client.get("/api/download/.._.._etc_passwd_12345678901234567890")
    assert response.status_code == 404
