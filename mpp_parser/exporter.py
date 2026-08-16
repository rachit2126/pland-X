import os
import logging
from typing import List, Optional, Dict, Any
import jpype

from .jvm import ensure_jvm_started
from .engine import MPPParser
from .schema import (
    MPPParseResultSchema,
    TaskModificationSchema,
    VerificationDetailsSchema,
    PredecessorSchema,
)

logger = logging.getLogger(__name__)


def _map_string_to_relation_type(type_str: str, RelationTypeClass):
    """Maps string FS, SS, FF, SF to MPXJ RelationType enum."""
    s = (type_str or "FS").upper().strip()
    if s == "SS" or "START_START" in s:
        return RelationTypeClass.START_START
    if s == "FF" or "FINISH_FINISH" in s:
        return RelationTypeClass.FINISH_FINISH
    if s == "SF" or "START_FINISH" in s:
        return RelationTypeClass.START_FINISH
    return RelationTypeClass.FINISH_START


class MPPExporter:
    """
    MPXJ-based exporter for reading, modifying, and writing Microsoft Project files.
    Exports updated programme data to MS Project-compatible MSPDI XML format and validates re-imported integrity.
    """

    def __init__(self):
        ensure_jvm_started()
        self.UniversalProjectReader = jpype.JClass("org.mpxj.reader.UniversalProjectReader")
        self.MSPDIWriter = jpype.JClass("org.mpxj.mspdi.MSPDIWriter")
        self.Duration = jpype.JClass("org.mpxj.Duration")
        self.TimeUnit = jpype.JClass("org.mpxj.TimeUnit")
        self.LocalDateTime = jpype.JClass("java.time.LocalDateTime")
        self.RelationType = jpype.JClass("org.mpxj.RelationType")
        self.Relation = jpype.JClass("org.mpxj.Relation")

    def modify_and_export(
        self,
        input_file: str,
        output_file: str,
        modifications: List[TaskModificationSchema]
    ) -> MPPParseResultSchema:
        """
        Reads input project file, applies task & predecessor modifications, writes updated file to output_file,
        and re-imports the exported file to return a verified MPPParseResultSchema with verification metadata.
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input project file not found: '{input_file}'")

        try:
            reader = self.UniversalProjectReader()
            project = reader.read(input_file)
        except Exception as e:
            raise ValueError(f"Unable to read input project file for modification: {e}") from e

        if project is None:
            raise ValueError("Unable to read input project file: Project reader returned null")

        # Map tasks by ID string for modification lookups
        tasks = project.getTasks()
        task_by_id: Dict[str, Any] = {}
        if tasks is not None:
            for i in range(tasks.size()):
                t = tasks.get(i)
                if t is not None and t.getID() is not None:
                    task_by_id[str(t.getID())] = t

        # Map modifications by task ID string
        mod_map: Dict[str, TaskModificationSchema] = {str(m.id): m for m in modifications}

        # Apply modifications
        for tid, mod in mod_map.items():
            if tid not in task_by_id:
                logger.warning(f"Task ID '{tid}' specified in modifications not found in project.")
                continue

            t = task_by_id[tid]

            if mod.name is not None:
                t.setName(mod.name)

            if mod.durationDays is not None:
                t.setDuration(self.Duration.getInstance(mod.durationDays, self.TimeUnit.DAYS))

            if mod.percentComplete is not None:
                t.setPercentageComplete(jpype.JDouble(mod.percentComplete))

            if mod.start is not None:
                try:
                    parts = [int(p) for p in mod.start.split("-")]
                    dt = self.LocalDateTime.of(parts[0], parts[1], parts[2], 8, 0)
                    t.setStart(dt)
                except Exception as dt_err:
                    logger.warning(f"Failed to parse start date '{mod.start}' for task {tid}: {dt_err}")

            if mod.finish is not None:
                try:
                    parts = [int(p) for p in mod.finish.split("-")]
                    dt = self.LocalDateTime.of(parts[0], parts[1], parts[2], 17, 0)
                    t.setFinish(dt)
                except Exception as dt_err:
                    logger.warning(f"Failed to parse finish date '{mod.finish}' for task {tid}: {dt_err}")

            # Predecessor modifications
            if mod.predecessors is not None:
                try:
                    mpxj_preds = t.getPredecessors()
                    if mpxj_preds is not None:
                        mpxj_preds.clear()

                    for p_spec in mod.predecessors:
                        pred_id = str(p_spec.id)
                        if pred_id in task_by_id:
                            pred_task = task_by_id[pred_id]
                            rel_type = _map_string_to_relation_type(p_spec.type, self.RelationType)
                            lag_dur = self.Duration.getInstance(p_spec.lagDays, self.TimeUnit.DAYS)

                            b = self.Relation.Builder()
                            b.successorTask(t).predecessorTask(pred_task).type(rel_type).lag(lag_dur)
                            t.addPredecessor(b)
                        else:
                            logger.warning(f"Predecessor task ID '{pred_id}' not found for task {tid}")
                except Exception as pred_err:
                    logger.warning(f"Failed to modify predecessors for task {tid}: {pred_err}")

        # Ensure output directory exists
        out_dir = os.path.dirname(os.path.abspath(output_file))
        os.makedirs(out_dir, exist_ok=True)

        try:
            writer = self.MSPDIWriter()
            writer.write(project, output_file)
        except Exception as e:
            raise ValueError(f"Failed to write exported project file: {e}") from e

        # Re-import exported file to verify integrity
        parser = MPPParser()
        result = parser.parse(output_file, source_filename=os.path.basename(output_file))

        # Perform verification checks comparing initial tasks vs exported re-imported tasks
        initial_parser = MPPParser()
        initial_result = initial_parser.parse(input_file)

        initial_map = {t.id: t for t in initial_result.tasks}
        reimport_map = {t.id: t for t in result.tasks}

        hierarchy_ok = True
        milestones_ok = True
        deps_ok = True

        for tid, init_t in initial_map.items():
            if tid in reimport_map:
                re_t = reimport_map[tid]

                # Hierarchy check
                if init_t.outlineLevel != re_t.outlineLevel or init_t.parentId != re_t.parentId:
                    # Skip checking parentId for explicitly modified tasks if hierarchy shifted
                    if tid not in mod_map:
                        hierarchy_ok = False

                # Milestone check
                if init_t.isMilestone != re_t.isMilestone:
                    milestones_ok = False

                # Dependency check (if task was not explicitly modified in predecessors)
                if tid not in mod_map or mod_map[tid].predecessors is None:
                    if len(init_t.predecessors) != len(re_t.predecessors):
                        deps_ok = False

        verification_details = VerificationDetailsSchema(
            tasksChecked=result.taskCount,
            hierarchyPreserved=hierarchy_ok,
            dependenciesPreserved=deps_ok,
            milestonesPreserved=milestones_ok,
        )

        result.exportFormat = "MSPDI XML"
        result.exportVerified = hierarchy_ok and deps_ok and milestones_ok
        result.verification = verification_details

        return result

    def generate_mspdi_xml(self, input_file: Optional[str] = None) -> bytes:
        """
        Generates valid MSPDI XML content as bytes.
        If input_file is provided, reads project file and exports to MSPDI XML bytes.
        Otherwise, builds a standard project schedule with tasks, hierarchy, dependencies, resources, and progress.
        """
        import tempfile
        if input_file and os.path.exists(input_file):
            reader = self.UniversalProjectReader()
            project = reader.read(input_file)
        else:
            ProjectFile = jpype.JClass("org.mpxj.ProjectFile")
            project = ProjectFile()
            props = project.getProjectProperties()
            props.setStartDate(self.LocalDateTime.of(2026, 1, 1, 8, 0))
            props.setFinishDate(self.LocalDateTime.of(2026, 6, 30, 17, 0))

            t1 = project.addTask()
            t1.setName("Phase 1: Mobilization & Planning")
            t1.setSummary(True)
            t1.setOutlineLevel(jpype.JInt(1))

            t2 = project.addTask()
            t2.setName("Site Establishment")
            t2.setStart(self.LocalDateTime.of(2026, 1, 1, 8, 0))
            t2.setFinish(self.LocalDateTime.of(2026, 1, 15, 17, 0))
            t2.setDuration(self.Duration.getInstance(10, self.TimeUnit.DAYS))
            t2.setPercentageComplete(jpype.JDouble(100.0))
            t2.setOutlineLevel(jpype.JInt(2))
            t1.addChildTask(t2)

            t3 = project.addTask()
            t3.setName("Foundation Signoff Milestone")
            t3.setMilestone(True)
            t3.setStart(self.LocalDateTime.of(2026, 1, 15, 17, 0))
            t3.setFinish(self.LocalDateTime.of(2026, 1, 15, 17, 0))
            t3.setDuration(self.Duration.getInstance(0, self.TimeUnit.DAYS))
            t3.setOutlineLevel(jpype.JInt(2))
            t1.addChildTask(t3)

            b = self.Relation.Builder()
            b.successorTask(t3).predecessorTask(t2).type(self.RelationType.FINISH_START).lag(self.Duration.getInstance(0, self.TimeUnit.DAYS))
            t3.addPredecessor(b)

        writer = self.MSPDIWriter()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
            tmp_path = tmp.name

        try:
            writer.write(project, tmp_path)
            with open(tmp_path, "rb") as f:
                content = f.read()
            return content
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

