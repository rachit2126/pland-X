from typing import List, Optional
from pydantic import BaseModel, Field, AliasChoices


class PredecessorSchema(BaseModel):
    id: str = Field(..., description="Predecessor task ID")
    type: str = Field(..., description="Relationship type: FS, SS, FF, SF")
    lagDays: float = Field(default=0.0, description="Lag days (can be positive or negative)")


class TaskSchema(BaseModel):
    id: str = Field(..., description="Task ID as string")
    wbs: Optional[str] = Field(default=None, description="WBS code string or null")
    name: str = Field(..., description="Task name")
    outlineLevel: int = Field(..., description="Outline hierarchy level")
    parentId: Optional[str] = Field(default=None, description="Parent task ID or null")
    isMilestone: bool = Field(default=False, description="Milestone flag")
    isSummary: bool = Field(default=False, description="Summary task flag")
    start: Optional[str] = Field(default=None, description="Start date YYYY-MM-DD")
    finish: Optional[str] = Field(default=None, description="Finish date YYYY-MM-DD")
    percentComplete: float = Field(default=0.0, description="Percentage complete (0-100)")
    durationDays: float = Field(default=0.0, description="Duration in days")
    predecessors: List[PredecessorSchema] = Field(default_factory=list)
    assignedResource: Optional[str] = Field(default=None, description="Raw assigned resource names")
    notes: Optional[str] = Field(default=None, description="Task notes")


class UnparsedWarningSchema(BaseModel):
    taskId: str = Field(..., description="Task ID associated with warning")
    reason: str = Field(..., description="Reason for warning")


class VerificationDetailsSchema(BaseModel):
    tasksChecked: int = Field(..., description="Number of tasks verified")
    hierarchyPreserved: bool = Field(default=True, description="Task hierarchy outlineLevel & parentId intact")
    dependenciesPreserved: bool = Field(default=True, description="Predecessor dependency links intact")
    milestonesPreserved: bool = Field(default=True, description="Milestone flags intact")


class MPPParseResultSchema(BaseModel):
    sourceFile: str = Field(..., description="Original file path or name")
    projectName: Optional[str] = Field(default=None, description="Project name or title")
    projectCalendar: Optional[str] = Field(default="Standard", description="Default project calendar name")
    parsedAt: str = Field(..., description="ISO 8601 timestamp of parsing")
    projectStart: Optional[str] = Field(default=None, description="Project start date YYYY-MM-DD")
    projectFinish: Optional[str] = Field(default=None, description="Project finish date YYYY-MM-DD")
    taskCount: int = Field(..., description="Total tasks extracted")
    tasks: List[TaskSchema] = Field(default_factory=list)
    unparsedWarnings: List[UnparsedWarningSchema] = Field(default_factory=list)
    exportFormat: Optional[str] = Field(default=None, description="Export file format if exported")
    exportVerified: Optional[bool] = Field(default=None, description="Export verification status")
    verification: Optional[VerificationDetailsSchema] = Field(default=None, description="Verification breakdown")


class ErrorResponseSchema(BaseModel):
    error: str = Field(..., description="Error description")


class TaskModificationSchema(BaseModel):
    id: str = Field(..., validation_alias=AliasChoices("id", "taskId"), description="Target task ID to modify")
    name: Optional[str] = Field(default=None, description="Updated task name")
    durationDays: Optional[float] = Field(default=None, description="Updated duration in days")
    start: Optional[str] = Field(default=None, description="Updated start date YYYY-MM-DD")
    finish: Optional[str] = Field(default=None, description="Updated finish date YYYY-MM-DD")
    percentComplete: Optional[float] = Field(default=None, description="Updated percent complete")
    predecessors: Optional[List[PredecessorSchema]] = Field(default=None, description="Updated predecessor relations")


class ExportRequestSchema(BaseModel):
    modifications: List[TaskModificationSchema] = Field(default_factory=list)
