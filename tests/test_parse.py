import os
import pytest
from mpp_parser.engine import parse_mpp_file

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
SAMPLE_MPP_PATH = os.path.join(FIXTURES_DIR, "sample_construction.mpp")


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


def test_task_hierarchy_baq_task_subtask():
    """Verify hierarchy correctly represents BAQ -> Task -> Sub-task using outlineLevel, parentId, WBS."""
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "test_hierarchy.xml"))
    result = parse_mpp_file(filepath)

    assert result.taskCount >= 4
    task_map = {t.name: t for t in result.tasks}

    baq_phase = task_map["Phase 1: Structure"]
    task_sec = task_map["Section A: Substructure"]
    footings = task_map["Pour Footings"]
    subtask_rebar = task_map["Rebar Placement"]

    # BAQ (Level 1)
    assert baq_phase.outlineLevel == 1
    assert baq_phase.parentId is None

    # Task (Level 2)
    assert task_sec.outlineLevel == 2
    assert task_sec.parentId == baq_phase.id

    # Sub-task (Level 3)
    assert footings.outlineLevel == 3
    assert footings.parentId == task_sec.id

    # Sub-task (Level 4)
    assert subtask_rebar.outlineLevel == 4
    assert subtask_rebar.parentId == footings.id


def test_milestone_handling():
    """Verify correct identification of milestones (isMilestone flag, duration, dates)."""
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "test_dependencies.xml"))
    result = parse_mpp_file(filepath)

    milestones = [t for t in result.tasks if t.isMilestone]
    assert len(milestones) >= 2

    m1 = next(t for t in milestones if "Commencement" in t.name)
    assert m1.isMilestone is True
    assert m1.durationDays == 0.0

    m2 = next(t for t in milestones if "Handover" in t.name)
    assert m2.isMilestone is True
    assert m2.durationDays == 0.0


def test_dependency_extraction():
    """Verify predecessor extraction including FS, SS, FF, SF and lag values."""
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "test_dependencies.xml"))
    result = parse_mpp_file(filepath)

    task_map = {t.name: t for t in result.tasks}
    m1 = task_map["Project Commencement Milestone"]
    dt1 = task_map["Foundation Design"]
    dt2 = task_map["Steel Procurement"]
    dt3 = task_map["Concrete Pouring"]
    dt4 = task_map["Inspection & Signoff"]

    # FS link
    assert len(dt1.predecessors) == 1
    assert dt1.predecessors[0].id == m1.id
    assert dt1.predecessors[0].type == "FS"

    # SS link with lag
    assert len(dt2.predecessors) == 1
    assert dt2.predecessors[0].id == dt1.id
    assert dt2.predecessors[0].type == "SS"
    assert dt2.predecessors[0].lag == 2.0
    assert dt2.predecessors[0].lagDays == 2.0

    # FF link with lag
    assert len(dt3.predecessors) == 1
    assert dt3.predecessors[0].id == dt2.id
    assert dt3.predecessors[0].type == "FF"
    assert dt3.predecessors[0].lag == 1.0

    # SF link
    assert len(dt4.predecessors) == 1
    assert dt4.predecessors[0].id == dt3.id
    assert dt4.predecessors[0].type == "SF"


def test_percent_complete():
    """Verify percent complete extraction."""
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    result = parse_mpp_file(filepath)

    t1 = next(t for t in result.tasks if t.name == "Site Setup")
    t2 = next(t for t in result.tasks if t.name == "Excavation Work")

    assert t1.percentComplete == 100.0
    assert t2.percentComplete == 50.0


def test_parse_native_mpp_file():
    """Verify parsing a native binary Microsoft Project (.mpp) file."""
    if not os.path.exists(SAMPLE_MPP_PATH):
        pytest.skip(f"Native MPP sample file not found at {SAMPLE_MPP_PATH}")

    result = parse_mpp_file(SAMPLE_MPP_PATH)
    assert result.taskCount == 800
    assert result.projectStart == "2025-08-04"
    assert result.projectFinish == "2026-12-10"
    assert len(result.tasks) == 800

    # Verify task attributes in native MPP
    t_first = result.tasks[1] # First non-summary task
    assert t_first.id == "1"
    assert t_first.outlineLevel == 1
    assert t_first.name == "ORMISTON RISE - BUILDING 2 & UNIT 80"


def test_multiple_sample_files():
    """Verify parser handles multiple sample files cleanly."""
    files = ["test_flat.xml", "test_hierarchy.xml", "test_dependencies.xml"]
    for fn in files:
        fp = os.path.abspath(os.path.join(FIXTURES_DIR, fn))
        res = parse_mpp_file(fp)
        assert res.taskCount > 0
        assert res.parsedAt is not None

