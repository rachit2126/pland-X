import os
import io
import pytest
from fastapi.testclient import TestClient

from mpp_parser.api import app
from mpp_parser.config import settings, Settings

client = TestClient(app)
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_api_unsupported_extension_returns_422():
    """Verify uploading file with unsupported extension (e.g. .exe) returns HTTP 422."""
    response = client.post(
        "/parse",
        files={"file": ("malicious.exe", b"binary content", "application/octet-stream")}
    )

    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert "Unsupported file format '.exe'" in data["error"]


def test_api_oversized_file_returns_413(monkeypatch):
    """Verify uploading file exceeding MAX_UPLOAD_SIZE_MB returns HTTP 413 Payload Too Large."""
    # Set max upload size to 1 KB for test
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)

    # 10 KB dummy content
    large_content = b"X" * (10 * 1024)

    response = client.post(
        "/parse",
        files={"file": ("large.mpp", large_content, "application/octet-stream")}
    )

    assert response.status_code == 413
    data = response.json()
    assert "error" in data
    assert "File size exceeds maximum allowed limit" in data["error"]


def test_config_environment_overrides(monkeypatch):
    """Verify Settings loads custom environment variables correctly."""
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "100")
    monkeypatch.setenv("ALLOWED_EXTENSIONS", ".mpp,.xml")
    monkeypatch.setenv("PORT", "9000")

    custom_settings = Settings()
    assert custom_settings.MAX_UPLOAD_SIZE_MB == 100
    assert custom_settings.max_upload_size_bytes == 100 * 1024 * 1024
    assert custom_settings.ALLOWED_EXTENSIONS == {".mpp", ".xml"}
    assert custom_settings.PORT == 9000
