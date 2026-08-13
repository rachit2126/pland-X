import logging
from typing import Dict, List, Optional
from datetime import datetime

from ..schema import MPPParseResultSchema
from .models import (
    PlanDProject,
    PlanDActivity,
    SyncResponse,
    DashboardMetrics,
)
from .mapper import MPPToPlanDXMapper

logger = logging.getLogger(__name__)


class ProgrammeRepository:
    """
    Decoupled repository adapter interface for storing and retrieving PlanD-X project data.
    Provides in-memory persistence with support for database adapters (Postgres, MongoDB, SQLite).
    """

    def __init__(self):
        self._store: Dict[str, PlanDProject] = {}

    def save_project(self, project: PlanDProject) -> PlanDProject:
        self._store[project.projectId] = project
        logger.info(f"Saved PlanD-X project '{project.projectId}' with {len(project.activities)} activities.")
        return project

    def get_project(self, project_id: str) -> Optional[PlanDProject]:
        return self._store.get(project_id)

    def list_projects(self) -> List[PlanDProject]:
        return list(self._store.values())


class ProgrammeService:
    """
    Service layer providing domain operations for construction programme management.
    """

    def __init__(self, repository: Optional[ProgrammeRepository] = None):
        self.repo = repository or ProgrammeRepository()

    def sync_mpp_data(self, project_id: str, mpp_data: MPPParseResultSchema) -> SyncResponse:
        """
        Syncs parsed MPP dataset into PlanD-X normalized programme structure.
        """
        project = MPPToPlanDXMapper.map_to_plandx_project(mpp_data, project_id=project_id)
        self.repo.save_project(project)

        warnings = [w.reason for w in mpp_data.unparsedWarnings] if mpp_data.unparsedWarnings else []

        return SyncResponse(
            projectId=project_id,
            syncStatus="success",
            activitiesImported=len(project.activities),
            warnings=warnings,
        )

    def get_programme(self, project_id: str) -> Optional[PlanDProject]:
        """
        Retrieves normalized PlanD-X project data.
        """
        return self.repo.get_project(project_id)

    def get_dashboard_metrics(self, project_id: str) -> DashboardMetrics:
        """
        Aggregates dashboard-ready programme telemetry (progress, delays, critical activities, milestones).
        """
        project = self.repo.get_project(project_id)

        if not project or not project.activities:
            return DashboardMetrics(
                progress=0.0,
                completedActivities=0,
                delayedActivities=0,
                criticalActivities=0,
                upcomingMilestones=0,
                totalActivities=0,
            )

        total_acts = len(project.activities)
        completed = sum(1 for a in project.activities if a.progressPercentage >= 100.0)
        delayed = sum(1 for a in project.activities if a.progressMetric and a.progressMetric.isDelayed)
        critical = sum(1 for a in project.activities if a.isSummary or (a.duration > 0 and len(a.dependencies) > 0))
        milestones = sum(1 for a in project.activities if a.milestone and a.progressPercentage < 100.0)

        total_progress_sum = sum(a.progressPercentage for a in project.activities)
        avg_progress = round(total_progress_sum / total_acts, 2) if total_acts > 0 else 0.0

        return DashboardMetrics(
            progress=avg_progress,
            completedActivities=completed,
            delayedActivities=delayed,
            criticalActivities=critical,
            upcomingMilestones=milestones,
            totalActivities=total_acts,
        )


# Global singleton instance for in-memory service
programme_service = ProgrammeService()
