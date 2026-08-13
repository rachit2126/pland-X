import pytest
from mpp_parser.schema import (
    TaskSchema,
    PredecessorSchema,
    MPPParseResultSchema,
    TaskModificationSchema,
    VerificationDetailsSchema,
)


def test_schema_task_validation():
    """Verify TaskSchema initialization and defaults."""
    task = TaskSchema(
        id="10",
        name="Test Task",
        outlineLevel=1,
        start="2026-01-01",
        finish="2026-01-05",
        durationDays=5.0,
        percentComplete=100.0,
    )
    assert task.id == "10"
    assert task.name == "Test Task"
    assert task.isMilestone is False
    assert task.isSummary is False
    assert task.parentId is None


def test_schema_task_modification_aliases():
    """Verify TaskModificationSchema supports both id and taskId via AliasChoices."""
    mod1 = TaskModificationSchema(**{"id": "25", "name": "Task Mod 1"})
    assert mod1.id == "25"
    assert mod1.name == "Task Mod 1"

    mod2 = TaskModificationSchema(**{"taskId": "30", "durationDays": 10.0})
    assert mod2.id == "30"
    assert mod2.durationDays == 10.0


def test_schema_parse_result_with_verification():
    """Verify MPPParseResultSchema with verification details."""
    ver = VerificationDetailsSchema(
        tasksChecked=100,
        hierarchyPreserved=True,
        dependenciesPreserved=True,
        milestonesPreserved=True,
    )
    result = MPPParseResultSchema(
        sourceFile="test.xml",
        projectName="Test Project",
        projectCalendar="Standard",
        parsedAt="2026-08-14T03:00:00Z",
        projectStart="2026-01-01",
        projectFinish="2026-06-01",
        taskCount=100,
        exportFormat="MSPDI XML",
        exportVerified=True,
        verification=ver,
    )
    assert result.exportFormat == "MSPDI XML"
    assert result.exportVerified is True
    assert result.verification.tasksChecked == 100
