"""API Health and Information Endpoint Unit Tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "PII Redaction Tool"
    # Ensure no internal paths or sensitive details exposed
    assert "filepath" not in data
    assert "secret" not in data


def test_api_info_endpoint():
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "PII Redaction Tool"
    assert data["version"] == "1.0.0"
    assert data["supported_file_type"] == ".docx"
    assert "PERSON" in data["pii_categories"]
    assert "EMAIL_ADDRESS" in data["pii_categories"]
