from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PlanDResource(BaseModel):
    resourceId: str = Field(..., description="Unique resource identifier")
    resourceName: str = Field(..., description="Resource or contractor name")
    resourceType: str = Field(default="Work", description="Resource classification: Work, Material, Cost, Subcontractor")


class PlanDDependency(BaseModel):
    predecessor: str = Field(..., description="Predecessor activity ID")
    successor: str = Field(..., description="Successor activity ID")
    relationshipType: str = Field(default="FS", description="Relationship type: FS, SS, FF, SF")
    lag: float = Field(default=0.0, description="Lag in days")


class BOQMapping(BaseModel):
    boqItemId: Optional[str] = Field(default=None, description="Linked BOQ Item ID")
    code: Optional[str] = Field(default=None, description="Cost code or BOQ pay item reference")
    quantity: Optional[float] = Field(default=None, description="Estimated work quantity")
    unit: Optional[str] = Field(default=None, description="Unit of measurement (m3, m2, tonnes, etc.)")
    costEstimate: Optional[float] = Field(default=None, description="Target budget or cost reference in currency")


class EvidenceRecord(BaseModel):
    evidenceId: str = Field(..., description="Unique evidence ID")
    activityId: str = Field(..., description="Target activity ID")
    type: str = Field(default="photo", description="Evidence type: photo, document, inspection, site_report")
    url: str = Field(..., description="File path or URL to verification evidence")
    verified: bool = Field(default=False, description="Verification status by site engineer")


class VendorMapping(BaseModel):
    vendorId: Optional[str] = Field(default=None, description="Vendor or Subcontractor ID")
    companyName: Optional[str] = Field(default=None, description="Contractor company name")
    package: Optional[str] = Field(default=None, description="Subcontract package name (e.g. MEP, Civil, Structure)")
    assignedActivities: List[str] = Field(default_factory=list, description="Activity IDs assigned to vendor")


class ProgressMetric(BaseModel):
    plannedPercent: float = Field(default=0.0, description="Baseline planned progress percentage")
    actualPercent: float = Field(default=0.0, description="Site reported actual progress percentage")
    variance: float = Field(default=0.0, description="Variance (actualPercent - plannedPercent)")
    isDelayed: bool = Field(default=False, description="Flag indicating schedule delay")
    delayDays: float = Field(default=0.0, description="Estimated delay in days")


class PlanDActivity(BaseModel):
    activityId: str = Field(..., description="Unique activity ID")
    WBS: Optional[str] = Field(default=None, description="WBS breakdown code")
    name: str = Field(..., description="Activity description")
    parentActivity: Optional[str] = Field(default=None, description="Parent summary activity ID")
    startDate: Optional[str] = Field(default=None, description="Start date YYYY-MM-DD")
    finishDate: Optional[str] = Field(default=None, description="Finish date YYYY-MM-DD")
    duration: float = Field(default=0.0, description="Duration in days")
    progressPercentage: float = Field(default=0.0, description="Progress percentage (0-100)")
    milestone: bool = Field(default=False, description="Milestone flag")
    isSummary: bool = Field(default=False, description="Summary group task flag")
    dependencies: List[PlanDDependency] = Field(default_factory=list)
    resources: List[PlanDResource] = Field(default_factory=list)
    boqMapping: Optional[BOQMapping] = Field(default=None)
    evidenceRecords: List[EvidenceRecord] = Field(default_factory=list)
    vendorMapping: Optional[VendorMapping] = Field(default=None)
    progressMetric: Optional[ProgressMetric] = Field(default=None)


class PlanDProject(BaseModel):
    projectId: str = Field(..., description="Project identifier")
    projectName: str = Field(..., description="Project name")
    startDate: Optional[str] = Field(default=None, description="Project start date")
    finishDate: Optional[str] = Field(default=None, description="Project finish date")
    calendar: str = Field(default="Standard", description="Default calendar")
    syncedAt: Optional[str] = Field(default=None, description="Last sync timestamp")
    activities: List[PlanDActivity] = Field(default_factory=list)


class SyncResponse(BaseModel):
    projectId: str = Field(..., description="Project identifier")
    syncStatus: str = Field(default="success", description="Sync execution status")
    activitiesImported: int = Field(..., description="Number of activities imported")
    warnings: List[str] = Field(default_factory=list, description="Import warnings")


class DashboardMetrics(BaseModel):
    progress: float = Field(..., description="Overall project progress percentage")
    completedActivities: int = Field(..., description="Count of completed activities (100%)")
    delayedActivities: int = Field(..., description="Count of delayed activities")
    criticalActivities: int = Field(..., description="Count of critical path activities")
    upcomingMilestones: int = Field(..., description="Count of upcoming milestones")
    totalActivities: int = Field(..., description="Total activities in project")
