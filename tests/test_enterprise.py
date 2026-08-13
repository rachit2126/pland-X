import os
import pytest
from fastapi.testclient import TestClient

from mpp_parser.api import app
from mpp_parser.security import sanitize_filename, validate_mime_type

client = TestClient(app)
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_request_correlation_id_middleware():
    """Verify X-Request-ID middleware generates UUID if omitted and preserves passed correlation ID."""
    # Test generated ID
    response1 = client.get("/api/v1/health")
    assert response1.status_code == 200
    assert "X-Request-ID" in response1.headers
    assert len(response1.headers["X-Request-ID"]) > 10

    # Test custom passed ID
    custom_id = "test-correlation-12345"
    response2 = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response2.status_code == 200
    assert response2.headers["X-Request-ID"] == custom_id


def test_metrics_endpoint():
    """Verify Prometheus metrics endpoints (/metrics and /api/v1/metrics)."""
    # Trigger an operation to increment counters
    flat_path = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    with open(flat_path, "rb") as f:
        client.post("/api/v1/parse", files={"file": ("test_flat.xml", f, "application/xml")})

    for endpoint in ["/metrics", "/api/v1/metrics"]:
        res = client.get(endpoint)
        assert res.status_code == 200
        assert "mpp_parse_total" in res.text
        assert "mpp_processing_seconds" in res.text
        assert "mpp_tasks_processed" in res.text


def test_mime_type_validation_unit():
    """Verify validate_mime_type security checks."""
    assert validate_mime_type("application/vnd.ms-project") is None
    assert validate_mime_type("application/xml") is None
    assert validate_mime_type("text/xml") is None
    assert validate_mime_type("application/octet-stream") is None

    err_resp = validate_mime_type("application/x-msdownload")
    assert err_resp is not None
    assert err_resp.status_code == 422


def test_filename_sanitization_unit():
    """Verify sanitize_filename removes path traversal vectors and unsafe characters."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("project; rm -rf.mpp") == "project__rm_-rf.mpp"
    assert sanitize_filename("") == "unnamed.mpp"


def test_api_v1_and_legacy_route_parity():
    """Verify route parity between /api/v1/ and legacy alias routes."""
    # Health checks
    h_v1 = client.get("/api/v1/health").json()
    h_leg = client.get("/health").json()
    assert h_v1["status"] == "ok"
    assert h_leg["status"] == "ok"

    # Parse parity
    flat_path = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    with open(flat_path, "rb") as f1:
        res_v1 = client.post("/api/v1/parse", files={"file": ("test_flat.xml", f1, "application/xml")})
    with open(flat_path, "rb") as f2:
        res_leg = client.post("/parse", files={"file": ("test_flat.xml", f2, "application/xml")})

    assert res_v1.status_code == 200
    assert res_leg.status_code == 200
    assert res_v1.json()["taskCount"] == res_leg.json()["taskCount"]
