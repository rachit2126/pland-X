from typing import List, Optional
from datetime import datetime

from ..schema import MPPParseResultSchema, TaskSchema
from .models import (
    PlanDProject,
    PlanDActivity,
    PlanDResource,
    PlanDDependency,
    BOQMapping,
    VendorMapping,
    ProgressMetric,
)
from .progress import calculate_progress_metric


class MPPToPlanDXMapper:
    """
    Converts extracted MPPParseResultSchema into normalized PlanD-X Programme models.
    """

    @staticmethod
    def map_to_plandx_project(mpp_data: MPPParseResultSchema, project_id: str = "proj-default") -> PlanDProject:
        activities: List[PlanDActivity] = []

        for task in mpp_data.tasks:
            # Map dependencies
            deps: List[PlanDDependency] = [
                PlanDDependency(
                    predecessor=str(pred.id),
                    successor=str(task.id),
                    relationshipType=pred.type,
                    lag=pred.lagDays,
                )
                for pred in task.predecessors
            ]

            # Map resources
            res_list: List[PlanDResource] = []
            vendor_map: Optional[VendorMapping] = None

            if task.assignedResource:
                r_names = [r.strip() for r in task.assignedResource.split(",") if r.strip()]
                for r_idx, r_name in enumerate(r_names):
                    r_id = f"res-{task.id}-{r_idx+1}"
                    r_type = "Subcontractor" if any(w in r_name.lower() for w in ["contractor", "subcontractor", "vendor"]) else "Work"
                    res_list.append(PlanDResource(resourceId=r_id, resourceName=r_name, resourceType=r_type))
                    
                    if r_type == "Subcontractor" and vendor_map is None:
                        vendor_map = VendorMapping(
                            vendorId=f"v-{hash(r_name) % 10000}",
                            companyName=r_name,
                            package=task.name,
                            assignedActivities=[str(task.id)]
                        )

            # Map BOQ reference fields
            boq_ref = BOQMapping(
                boqItemId=f"boq-{task.id}",
                code=f"COST-{task.id}",
                quantity=1.0 if not task.isMilestone else 0.0,
                unit="ls" if not task.isMilestone else "ea",
                costEstimate=task.durationDays * 10000.0 if not task.isMilestone else 0.0,
            )

            # Calculate progress metric (planned vs actual variance)
            prog_metric = calculate_progress_metric(
                start_date=task.start,
                finish_date=task.finish,
                actual_percent=task.percentComplete,
                is_milestone=task.isMilestone
            )

            act = PlanDActivity(
                activityId=str(task.id),
                WBS=task.wbs,
                name=task.name,
                parentActivity=str(task.parentId) if task.parentId else None,
                startDate=task.start,
                finishDate=task.finish,
                duration=task.durationDays,
                progressPercentage=task.percentComplete,
                milestone=task.isMilestone,
                isSummary=task.isSummary,
                dependencies=deps,
                resources=res_list,
                boqMapping=boq_ref,
                evidenceRecords=[],
                vendorMapping=vendor_map,
                progressMetric=prog_metric,
            )
            activities.append(act)

        project_name = mpp_data.projectName or mpp_data.sourceFile or "PlanD Construction Project"
        synced_now = datetime.utcnow().isoformat() + "Z"

        return PlanDProject(
            projectId=project_id,
            projectName=project_name,
            startDate=mpp_data.projectStart,
            finishDate=mpp_data.projectFinish,
            calendar=mpp_data.projectCalendar or "Standard",
            syncedAt=synced_now,
            activities=activities,
        )
