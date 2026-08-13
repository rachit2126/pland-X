import os
import pytest
from fastapi.testclient import TestClient

from mpp_parser.api import app
from mpp_parser.engine import parse_mpp_file
from mpp_parser.plandx.models import (
    PlanDProject,
    PlanDActivity,
    BOQMapping,
    EvidenceRecord,
    VendorMapping,
    ProgressMetric,
)
from mpp_parser.plandx.mapper import MPPToPlanDXMapper
from mpp_parser.plandx.progress import calculate_progress_metric
from mpp_parser.plandx.repository import programme_service

client = TestClient(app)
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_plandx_schema_validation():
    """Verify initialization of PlanD-X DTO models."""
    boq = BOQMapping(boqItemId="boq-1", code="COST-100", quantity=50.0, unit="m3", costEstimate=500000.0)
    assert boq.code == "COST-100"
    assert boq.costEstimate == 500000.0

    ev = EvidenceRecord(evidenceId="ev-1", activityId="10", type="photo", url="/site/photo1.jpg", verified=True)
    assert ev.verified is True

    vendor = VendorMapping(vendorId="v-1", companyName="ABC Electrical Contractor", package="MEP Works", assignedActivities=["10"])
    assert vendor.companyName == "ABC Electrical Contractor"


def test_mpp_to_plandx_mapper():
    """Verify MPPToPlanDXMapper converts MPPParseResultSchema to PlanDProject."""
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    mpp_data = parse_mpp_file(filepath)

    project = MPPToPlanDXMapper.map_to_plandx_project(mpp_data, project_id="proj-demo-1")

    assert project.projectId == "proj-demo-1"
    assert len(project.activities) == mpp_data.taskCount
    
    act1 = next(a for a in project.activities if a.activityId == "1")
    assert act1.name == "Site Setup"
    assert act1.boqMapping is not None
    assert act1.boqMapping.code == "COST-1"


def test_progress_variance_calculation():
    """Verify calculate_progress_metric schedule variance calculation."""
    # On schedule
    metric1 = calculate_progress_metric("2026-01-01", "2026-01-10", actual_percent=100.0)
    assert metric1.actualPercent == 100.0

    # Delayed task
    metric2 = calculate_progress_metric("2020-01-01", "2020-01-10", actual_percent=20.0)
    assert metric2.plannedPercent == 100.0
    assert metric2.variance == -80.0
    assert metric2.isDelayed is True
    assert metric2.delayDays > 0.0


def test_programme_service_and_repository():
    """Verify ProgrammeService sync, retrieval, and dashboard calculations."""
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "test_dependencies.xml"))
    mpp_data = parse_mpp_file(filepath)

    sync_res = programme_service.sync_mpp_data("proj-sync-test", mpp_data)
    assert sync_res.syncStatus == "success"
    assert sync_res.activitiesImported == mpp_data.taskCount

    project = programme_service.get_programme("proj-sync-test")
    assert project is not None
    assert project.projectId == "proj-sync-test"

    dash = programme_service.get_dashboard_metrics("proj-sync-test")
    assert dash.totalActivities == mpp_data.taskCount
    assert "progress" in dash.model_dump()


def test_plandx_api_endpoints():
    """Verify FastAPI endpoints /api/v1/projects/{id}/sync, /programme, /dashboard."""
    flat_path = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))

    # 1. Sync
    with open(flat_path, "rb") as f:
        sync_res = client.post(
            "/api/v1/projects/proj-api-test/sync",
            files={"file": ("test_flat.xml", f, "application/xml")}
        )

    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["projectId"] == "proj-api-test"
    assert sync_data["syncStatus"] == "success"
    assert sync_data["activitiesImported"] >= 2

    # 2. Programme
    prog_res = client.get("/api/v1/projects/proj-api-test/programme")
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["projectId"] == "proj-api-test"
    assert len(prog_data["activities"]) >= 2

    # 3. Dashboard
    dash_res = client.get("/api/v1/projects/proj-api-test/dashboard")
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "progress" in dash_data
    assert dash_data["totalActivities"] >= 2
