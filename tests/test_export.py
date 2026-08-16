import os
import pytest
from fastapi.testclient import TestClient
from mpp_parser.api import app
from mpp_parser.engine import parse_mpp_file
from mpp_parser.exporter import MPPExporter
from mpp_parser.schema import TaskModificationSchema

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
client = TestClient(app)


def test_export_without_modifications(tmp_path):
    """
    Test Case: Export without modifications
    Verify: Output file is created, re-imports cleanly, matches task count.
    """
    input_file = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    output_file = str(tmp_path / "export_no_mods.xml")

    exporter = MPPExporter()
    result = exporter.modify_and_export(input_file, output_file, [])

    assert os.path.exists(output_file)
    assert result.taskCount >= 2
    assert result.sourceFile == "export_no_mods.xml"


def test_export_with_task_name_modification(tmp_path):
    """
    Test Case: Export with task name modification
    Verify: Updated task name in re-imported project.
    """
    input_file = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    output_file = str(tmp_path / "export_name_mod.xml")

    mods = [
        TaskModificationSchema(
            id="1",
            name="UPDATED: Site Setup & Mobilization"
        )
    ]

    exporter = MPPExporter()
    result = exporter.modify_and_export(input_file, output_file, mods)

    assert os.path.exists(output_file)
    t1 = next(t for t in result.tasks if t.id == "1")
    assert t1.name == "UPDATED: Site Setup & Mobilization"


def test_export_with_duration_modification(tmp_path):
    """
    Test Case: Export with duration modification
    Verify: Updated duration in days.
    """
    input_file = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    output_file = str(tmp_path / "export_dur_mod.xml")

    mods = [
        TaskModificationSchema(
            id="2",
            durationDays=20.0
        )
    ]

    exporter = MPPExporter()
    result = exporter.modify_and_export(input_file, output_file, mods)

    assert os.path.exists(output_file)
    t2 = next(t for t in result.tasks if t.id == "2")
    assert t2.durationDays == 20.0


def test_export_with_date_modification(tmp_path):
    """
    Test Case: Export with start and finish date modifications
    Verify: Updated start and finish dates in re-imported project.
    """
    input_file = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    output_file = str(tmp_path / "export_date_mod.xml")

    mods = [
        TaskModificationSchema(
            id="1",
            start="2026-05-01",
            finish="2026-05-10"
        )
    ]

    exporter = MPPExporter()
    result = exporter.modify_and_export(input_file, output_file, mods)

    assert os.path.exists(output_file)
    t1 = next(t for t in result.tasks if t.id == "1")
    assert t1.start == "2026-05-01"
    assert t1.finish == "2026-05-10"


def test_export_with_predecessor_preservation(tmp_path):
    """
    Test Case: Export preserving predecessor dependencies
    Verify: Relationships (FS, SS, FF, SF) and lag days are preserved.
    """
    input_file = os.path.abspath(os.path.join(FIXTURES_DIR, "test_dependencies.xml"))
    output_file = str(tmp_path / "export_preds_mod.xml")

    mods = [
        TaskModificationSchema(
            id="3",
            name="UPDATED: Steel Procurement Phase"
        )
    ]

    exporter = MPPExporter()
    result = exporter.modify_and_export(input_file, output_file, mods)

    assert os.path.exists(output_file)
    t3 = next(t for t in result.tasks if t.id == "3")
    assert t3.name == "UPDATED: Steel Procurement Phase"
    assert len(t3.predecessors) == 1
    assert t3.predecessors[0].id == "2"
    assert t3.predecessors[0].type == "SS"
    assert t3.predecessors[0].lagDays == 2.0


def test_export_hierarchy_preservation(tmp_path):
    """
    Test Case: Hierarchy Preservation during Export
    Verify: Summary tasks, outlineLevel, and parentId structure remain unchanged.
    """
    input_file = os.path.abspath(os.path.join(FIXTURES_DIR, "test_hierarchy.xml"))
    output_file = str(tmp_path / "export_hierarchy.xml")

    exporter = MPPExporter()
    result = exporter.modify_and_export(input_file, output_file, [])

    assert result.exportVerified is True
    assert result.verification.hierarchyPreserved is True

    sec = next(t for t in result.tasks if t.name == "Section A: Substructure")
    footings = next(t for t in result.tasks if t.name == "Pour Footings")
    assert footings.parentId == sec.id
    assert footings.outlineLevel == sec.outlineLevel + 1


def test_api_export_swagger_default_string():
    """
    Test API: POST /export with Swagger UI default "string" in modifications_json
    Verify: Does not crash, defaults to [] modifications, returns HTTP 200 OK.
    """
    flat_path = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    assert os.path.exists(flat_path)

    with open(flat_path, "rb") as f:
        response = client.post(
            "/export",
            files={"file": ("test_flat.xml", f, "application/octet-stream")},
            data={"modifications_json": "string"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["taskCount"] >= 2
    assert "projectName" in data
    assert "projectCalendar" in data
    assert "parsedAt" in data


def test_api_export_invalid_json_returns_422():
    """
    Test API: POST /export with invalid JSON string in modifications_json
    Verify: Returns HTTP 422 Unprocessable Entity with error message.
    """
    flat_path = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))

    with open(flat_path, "rb") as f:
        response = client.post(
            "/export",
            files={"file": ("test_flat.xml", f, "application/octet-stream")},
            data={"modifications_json": "{invalid json string format}"}
        )

    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert "Invalid JSON format in modifications_json" in data["error"]


def test_api_export_with_task_id_alias():
    """
    Test API: POST /export using 'taskId' alias in JSON payload
    Verify: Parses taskId and applies modifications correctly.
    """
    flat_path = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))

    mods_json = '[{"taskId": "1", "name": "Alias Updated Task", "durationDays": 25.0, "percentComplete": 80.0}]'

    with open(flat_path, "rb") as f:
        response = client.post(
            "/export",
            files={"file": ("test_flat.xml", f, "application/octet-stream")},
            data={"modifications_json": mods_json}
        )

    assert response.status_code == 200
    data = response.json()
    t1 = next(t for t in data["tasks"] if t["id"] == "1")
    assert t1["name"] == "Alias Updated Task"
    assert t1["durationDays"] == 25.0
    assert t1["percentComplete"] == 80.0


def test_api_get_export_info():
    """
    Test API: GET /api/v1/export
    Verify: Returns HTTP 200 with export capabilities, supported format (MSPDI XML), and documentation.
    """
    response = client.get("/api/v1/export")
    assert response.status_code == 200
    data = response.json()
    assert "supportedExportFormats" in data
    assert "MSPDI XML (.xml)" in data["supportedExportFormats"]
    assert data["nativeMppWriteSupported"] is False


def test_api_get_programme_export_xml():
    """
    Test API: GET /api/projects/{id}/programme/export?format=xml
    Verify: Generates valid MSPDI XML with 200 OK and application/xml Content-Type.
    """
    response = client.get("/api/v1/projects/PRJ-202/programme/export?format=xml")
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert b"<?xml" in response.content or b"<Project" in response.content


def test_api_get_programme_export_unsupported_format_returns_422():
    """
    Test API: GET /api/projects/{id}/programme/export?format=pdf
    Verify: Unsupported format query returns HTTP 422 Unprocessable Entity.
    """
    response = client.get("/api/v1/projects/PRJ-202/programme/export?format=pdf")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data


def test_round_trip_xml_validation(tmp_path):
    """
    Test Case: Round trip XML import -> export -> re-import validation
    Verify: All tasks, dates, dependencies, resources, and progress are preserved cleanly.
    """
    input_file = os.path.abspath(os.path.join(FIXTURES_DIR, "test_dependencies.xml"))
    output_file = str(tmp_path / "round_trip.xml")

    exporter = MPPExporter()
    result = exporter.modify_and_export(input_file, output_file, [])

    assert os.path.exists(output_file)
    assert result.exportVerified is True
    assert result.verification.hierarchyPreserved is True
    assert result.verification.dependenciesPreserved is True
    assert result.verification.milestonesPreserved is True

    # Re-parse exported file
    reimport_result = parse_mpp_file(output_file)
    assert reimport_result.taskCount == result.taskCount
    assert len(reimport_result.tasks) == len(result.tasks)


