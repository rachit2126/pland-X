import os
import pytest
from fastapi.testclient import TestClient
from mpp_parser.api import app

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
client = TestClient(app)


def test_api_health_check():
    """Verify /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_parse_valid_mpp():
    """Verify POST /parse with valid MPP returns 200 OK and expected JSON schema."""
    flat_path = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    assert os.path.exists(flat_path)

    with open(flat_path, "rb") as f:
        response = client.post(
            "/parse",
            files={"file": ("test_flat.xml", f, "application/octet-stream")}
        )

    assert response.status_code == 200
    data = response.json()

    assert data["sourceFile"] == "test_flat.xml"
    assert data["taskCount"] >= 2
    assert "projectStart" in data
    assert "tasks" in data
    assert len(data["tasks"]) >= 2
    assert isinstance(data["unparsedWarnings"], list)


def test_api_parse_corrupted_file_returns_422():
    """
    Verify POST /parse with corrupted file returns HTTP 422 Unprocessable Entity
    with {"error": "Unable to parse MPP file..."} payload.
    """
    corrupt_path = os.path.abspath(os.path.join(FIXTURES_DIR, "corrupted.mpp"))
    assert os.path.exists(corrupt_path)

    with open(corrupt_path, "rb") as f:
        response = client.post(
            "/parse",
            files={"file": ("corrupted.mpp", f, "application/octet-stream")}
        )

    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"] == "Unable to parse MPP file"
