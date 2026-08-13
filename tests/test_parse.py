import os
import pytest
from mpp_parser.engine import parse_mpp_file

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
REAL_MPP_PATH = "/Users/apple/Downloads/260728 - Ormiston Bld 2 & Unit 80 - Construction Program - Rev 2.mpp"


def test_parse_flat_structure():
    """Verify flat task structure parsing."""
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    result = parse_mpp_file(filepath)

    assert result.sourceFile == "test_flat.xml"
    assert result.taskCount >= 2
    assert result.projectStart == "2026-01-01"

    t1 = next(t for t in result.tasks if t.name == "Site Setup")
    assert t1.start == "2026-01-01"
    assert t1.finish == "2026-01-05"
    assert t1.durationDays == 5.0
    assert t1.percentComplete == 100.0


def test_parse_hierarchy_preservation():
    """Verify WBS and hierarchy outlineLevel & parentId structure."""
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "test_hierarchy.xml"))
    result = parse_mpp_file(filepath)

    assert result.taskCount >= 4
    task_map = {t.name: t for t in result.tasks}

    phase = task_map["Phase 1: Structure"]
    sec = task_map["Section A: Substructure"]
    footings = task_map["Pour Footings"]
    rebar = task_map["Rebar Placement"]

    assert phase.outlineLevel == 1
    assert phase.parentId is None
    assert sec.outlineLevel == 2
    assert sec.parentId == phase.id
    assert footings.outlineLevel == 3
    assert footings.parentId == sec.id
    assert rebar.outlineLevel == 4
    assert rebar.parentId == footings.id


def test_parse_real_world_construction_mpp():
    """Verify parsing real-world 800-task construction MPP file."""
    if not os.path.exists(REAL_MPP_PATH):
        pytest.skip(f"Real MPP file not found at {REAL_MPP_PATH}")

    result = parse_mpp_file(REAL_MPP_PATH)
    assert result.taskCount == 800
    assert result.projectStart == "2025-08-04"
    assert result.projectFinish == "2026-12-10"
    assert len(result.tasks) == 800
