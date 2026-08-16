import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple
import jpype

from .jvm import ensure_jvm_started
from .schema import (
    MPPParseResultSchema,
    TaskSchema,
    PredecessorSchema,
    UnparsedWarningSchema,
)

logger = logging.getLogger(__name__)


def _format_date(date_obj) -> Optional[str]:
    """Formats Java date/LocalDateTime/Date or Python date to YYYY-MM-DD string."""
    if date_obj is None:
        return None
    try:
        s = str(date_obj).strip()
        if not s:
            return None
        # Handles "2025-08-04T08:00", "2025-08-04 08:00:00", "2025-08-04"
        if "T" in s:
            return s.split("T")[0]
        if " " in s:
            return s.split(" ")[0]
        if len(s) >= 10:
            return s[:10]
        return s
    except Exception:
        return None


def _map_relation_type(type_obj) -> str:
    """Maps MPXJ RelationType enum to FS, SS, FF, SF."""
    if type_obj is None:
        return "FS"
    name = str(type_obj.name() if hasattr(type_obj, "name") else type_obj).upper()
    if "START_START" in name or name == "SS":
        return "SS"
    if "FINISH_FINISH" in name or name == "FF":
        return "FF"
    if "START_FINISH" in name or name == "SF":
        return "SF"
    return "FS"


class MPPParser:
    """
    Core engine for parsing Microsoft Project (.MPP) files using MPXJ.
    """

    def __init__(self):
        ensure_jvm_started()
        self.UniversalProjectReader = jpype.JClass("org.mpxj.reader.UniversalProjectReader")

    def parse(self, file_path: str, source_filename: Optional[str] = None) -> MPPParseResultSchema:
        """
        Parses an MPP file at file_path and returns structured MPPParseResultSchema.
        Raises ValueError or Exception if file cannot be parsed or does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        source_name = source_filename or os.path.basename(file_path)
        parsed_at = datetime.now(timezone.utc).isoformat()

        try:
            reader = self.UniversalProjectReader()
            project = reader.read(file_path)
        except Exception as e:
            logger.error(f"Failed to parse MPP file {file_path}: {e}")
            raise ValueError(f"Unable to parse MPP file: {e}") from e

        if project is None:
            raise ValueError("Unable to parse MPP file: project reader returned null")

        # Project level properties
        props = project.getProjectProperties()
        proj_start = _format_date(props.getStartDate()) if props else None
        proj_finish = _format_date(props.getFinishDate()) if props else None

        proj_name = source_name
        calendar_name = "Standard"
        if props:
            if props.getProjectTitle():
                proj_name = str(props.getProjectTitle()).strip()
            elif props.getName():
                proj_name = str(props.getName()).strip()

            def_cal = props.getDefaultCalendar()
            if def_cal and def_cal.getName():
                calendar_name = str(def_cal.getName()).strip()

        extracted_tasks: List[TaskSchema] = []
        warnings: List[UnparsedWarningSchema] = []

        mpxj_tasks = project.getTasks()
        if mpxj_tasks is None:
            return MPPParseResultSchema(
                sourceFile=source_name,
                parsedAt=parsed_at,
                projectStart=proj_start,
                projectFinish=proj_finish,
                taskCount=0,
                tasks=[],
                unparsedWarnings=warnings,
            )

        last_task_at_level = {}
        for i in range(mpxj_tasks.size()):
            t = mpxj_tasks.get(i)
            if t is None:
                continue

            task_id = str(t.getID()) if t.getID() is not None else None
            if task_id is None:
                continue

            # Task level fields
            name = str(t.getName()) if t.getName() is not None else f"Task {task_id}"
            wbs = str(t.getWBS()) if t.getWBS() is not None else None
            outline_level = int(t.getOutlineLevel()) if t.getOutlineLevel() is not None else 1

            # Parent ID handling (BAQ -> Task -> Sub-task hierarchy)
            parent_task = t.getParentTask()
            parent_id = None
            if parent_task is not None and parent_task.getID() is not None:
                pid = str(parent_task.getID())
                # If parent ID is 0 or outline level is 1, root tasks have parentId null
                if pid != "0" and pid != task_id and outline_level > 1:
                    parent_id = pid
            
            # Fallback to level stack if parent task not directly provided
            if parent_id is None and outline_level > 1:
                parent_id = last_task_at_level.get(outline_level - 1)

            last_task_at_level[outline_level] = task_id

            is_milestone = bool(t.getMilestone()) if t.getMilestone() is not None else False
            is_summary = bool(t.getSummary()) if t.getSummary() is not None else False

            start_date = _format_date(t.getStart())
            finish_date = _format_date(t.getFinish())

            # Percentage complete
            pct = 0.0
            if t.getPercentageComplete() is not None:
                try:
                    pct = round(float(t.getPercentageComplete()), 2)
                except (ValueError, TypeError):
                    warnings.append(
                        UnparsedWarningSchema(
                            taskId=task_id,
                            reason=f"Invalid percentage complete value: {t.getPercentageComplete()}"
                        )
                    )

            # Duration in days
            duration_days = 0.0
            if t.getDuration() is not None:
                try:
                    dur_obj = t.getDuration()
                    duration_days = round(float(dur_obj.getDuration()), 2)
                except Exception as e:
                    warnings.append(
                        UnparsedWarningSchema(
                            taskId=task_id,
                            reason=f"Failed to parse task duration: {e}"
                        )
                    )

            # Predecessors
            predecessors: List[PredecessorSchema] = []
            try:
                mpxj_preds = t.getPredecessors()
                if mpxj_preds is not None and mpxj_preds.size() > 0:
                    for p_idx in range(mpxj_preds.size()):
                        rel = mpxj_preds.get(p_idx)
                        if rel is None:
                            continue
                        pred_task = rel.getPredecessorTask()
                        if pred_task is None or pred_task.getID() is None:
                            warnings.append(
                                UnparsedWarningSchema(
                                    taskId=task_id,
                                    reason=f"Predecessor relation at index {p_idx} missing target task"
                                )
                            )
                            continue

                        pred_id = str(pred_task.getID())
                        rel_type = _map_relation_type(rel.getType())
                        lag_days = 0.0
                        lag_obj = rel.getLag()
                        if lag_obj is not None:
                            try:
                                lag_days = round(float(lag_obj.getDuration()), 2)
                            except Exception:
                                pass

                        predecessors.append(
                            PredecessorSchema(
                                id=pred_id,
                                type=rel_type,
                                lag=lag_days,
                                lagDays=lag_days,
                            )
                        )
            except Exception as e:
                warnings.append(
                    UnparsedWarningSchema(
                        taskId=task_id,
                        reason=f"Error extracting predecessors: {e}"
                    )
                )

            # Assigned resources
            assigned_resource = None
            try:
                assns = t.getResourceAssignments()
                if assns is not None and assns.size() > 0:
                    names = []
                    for a_idx in range(assns.size()):
                        assn = assns.get(a_idx)
                        if assn is not None and assn.getResource() is not None:
                            res_name = assn.getResource().getName()
                            if res_name:
                                names.append(str(res_name).strip())
                    if names:
                        assigned_resource = ", ".join(names)
            except Exception as e:
                warnings.append(
                    UnparsedWarningSchema(
                        taskId=task_id,
                        reason=f"Missing or corrupted resource assignment: {e}"
                    )
                )

            # Notes
            notes = None
            if t.getNotes() is not None:
                notes_str = str(t.getNotes()).strip()
                if notes_str:
                    notes = notes_str

            extracted_tasks.append(
                TaskSchema(
                    id=task_id,
                    wbs=wbs,
                    name=name,
                    outlineLevel=outline_level,
                    parentId=parent_id,
                    isMilestone=is_milestone,
                    isSummary=is_summary,
                    start=start_date,
                    finish=finish_date,
                    percentComplete=pct,
                    durationDays=duration_days,
                    predecessors=predecessors,
                    assignedResource=assigned_resource,
                    notes=notes,
                )
            )

        return MPPParseResultSchema(
            sourceFile=source_name,
            projectName=proj_name,
            projectCalendar=calendar_name,
            parsedAt=parsed_at,
            projectStart=proj_start,
            projectFinish=proj_finish,
            taskCount=len(extracted_tasks),
            tasks=extracted_tasks,
            unparsedWarnings=warnings,
        )


_global_parser: Optional[MPPParser] = None

def parse_mpp_file(file_path: str, source_filename: Optional[str] = None) -> MPPParseResultSchema:
    """Convenience function to parse an MPP file using a singleton parser instance."""
    global _global_parser
    if _global_parser is None:
        _global_parser = MPPParser()
    return _global_parser.parse(file_path, source_filename=source_filename)
