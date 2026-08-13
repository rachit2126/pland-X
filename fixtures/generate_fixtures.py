import os
import glob
import jpype
from mpp_parser.jvm import ensure_jvm_started

def generate_all_fixtures(output_dir: str):
    """
    Generates test fixture files for automated testing using MPXJ.
    """
    ensure_jvm_started()

    ProjectFile = jpype.JClass("org.mpxj.ProjectFile")
    RelationType = jpype.JClass("org.mpxj.RelationType")
    Relation = jpype.JClass("org.mpxj.Relation")
    Duration = jpype.JClass("org.mpxj.Duration")
    TimeUnit = jpype.JClass("org.mpxj.TimeUnit")
    MSPDIWriter = jpype.JClass("org.mpxj.mspdi.MSPDIWriter")
    LocalDateTime = jpype.JClass("java.time.LocalDateTime")

    os.makedirs(output_dir, exist_ok=True)
    writer = MSPDIWriter()

    # -------------------------------------------------------------
    # Test Case 1: Simple Flat Task Structure
    # -------------------------------------------------------------
    pf1 = ProjectFile()
    props1 = pf1.getProjectProperties()
    props1.setStartDate(LocalDateTime.of(2026, 1, 1, 8, 0))
    props1.setFinishDate(LocalDateTime.of(2026, 1, 15, 17, 0))

    t1 = pf1.addTask()
    t1.setName("Site Setup")
    t1.setStart(LocalDateTime.of(2026, 1, 1, 8, 0))
    t1.setFinish(LocalDateTime.of(2026, 1, 5, 17, 0))
    t1.setDuration(Duration.getInstance(5, TimeUnit.DAYS))
    t1.setPercentageComplete(jpype.JDouble(100.0))

    t2 = pf1.addTask()
    t2.setName("Excavation Work")
    t2.setStart(LocalDateTime.of(2026, 1, 6, 8, 0))
    t2.setFinish(LocalDateTime.of(2026, 1, 15, 17, 0))
    t2.setDuration(Duration.getInstance(10, TimeUnit.DAYS))
    t2.setPercentageComplete(jpype.JDouble(50.0))

    flat_path = os.path.join(output_dir, "test_flat.xml")
    writer.write(pf1, flat_path)

    # -------------------------------------------------------------
    # Test Case 2: Multi-Level Hierarchy
    # -------------------------------------------------------------
    pf2 = ProjectFile()
    props2 = pf2.getProjectProperties()
    props2.setStartDate(LocalDateTime.of(2026, 2, 1, 8, 0))

    p_phase = pf2.addTask()
    p_phase.setName("Phase 1: Structure")
    p_phase.setSummary(True)
    p_phase.setOutlineLevel(jpype.JInt(1))

    p_sec = pf2.addTask()
    p_sec.setName("Section A: Substructure")
    p_sec.setSummary(True)
    p_sec.setOutlineLevel(jpype.JInt(2))
    p_phase.addChildTask(p_sec)

    p_task1 = pf2.addTask()
    p_task1.setName("Pour Footings")
    p_task1.setStart(LocalDateTime.of(2026, 2, 1, 8, 0))
    p_task1.setFinish(LocalDateTime.of(2026, 2, 5, 17, 0))
    p_task1.setDuration(Duration.getInstance(5, TimeUnit.DAYS))
    p_task1.setOutlineLevel(jpype.JInt(3))
    p_sec.addChildTask(p_task1)

    p_sub1 = pf2.addTask()
    p_sub1.setName("Rebar Placement")
    p_sub1.setStart(LocalDateTime.of(2026, 2, 1, 8, 0))
    p_sub1.setFinish(LocalDateTime.of(2026, 2, 3, 17, 0))
    p_sub1.setDuration(Duration.getInstance(3, TimeUnit.DAYS))
    p_sub1.setOutlineLevel(jpype.JInt(4))
    p_task1.addChildTask(p_sub1)

    hier_path = os.path.join(output_dir, "test_hierarchy.xml")
    writer.write(pf2, hier_path)

    # -------------------------------------------------------------
    # Test Case 3: Dependencies (FS, SS, FF, SF + Lag) & Milestones
    # -------------------------------------------------------------
    pf3 = ProjectFile()
    props3 = pf3.getProjectProperties()
    props3.setStartDate(LocalDateTime.of(2026, 3, 1, 8, 0))

    m1 = pf3.addTask()
    m1.setName("Project Commencement Milestone")
    m1.setMilestone(True)
    m1.setDuration(Duration.getInstance(0, TimeUnit.DAYS))
    m1.setStart(LocalDateTime.of(2026, 3, 1, 8, 0))
    m1.setFinish(LocalDateTime.of(2026, 3, 1, 8, 0))

    dt1 = pf3.addTask()
    dt1.setName("Foundation Design")
    dt1.setStart(LocalDateTime.of(2026, 3, 1, 8, 0))
    dt1.setDuration(Duration.getInstance(10, TimeUnit.DAYS))
    b1 = Relation.Builder()
    b1.successorTask(dt1).predecessorTask(m1).type(RelationType.FINISH_START).lag(Duration.getInstance(0, TimeUnit.DAYS))
    dt1.addPredecessor(b1)

    dt2 = pf3.addTask()
    dt2.setName("Steel Procurement")
    dt2.setStart(LocalDateTime.of(2026, 3, 5, 8, 0))
    dt2.setDuration(Duration.getInstance(8, TimeUnit.DAYS))
    b2 = Relation.Builder()
    b2.successorTask(dt2).predecessorTask(dt1).type(RelationType.START_START).lag(Duration.getInstance(2, TimeUnit.DAYS))
    dt2.addPredecessor(b2)

    dt3 = pf3.addTask()
    dt3.setName("Concrete Pouring")
    dt3.setStart(LocalDateTime.of(2026, 3, 15, 8, 0))
    dt3.setDuration(Duration.getInstance(5, TimeUnit.DAYS))
    b3 = Relation.Builder()
    b3.successorTask(dt3).predecessorTask(dt2).type(RelationType.FINISH_FINISH).lag(Duration.getInstance(1, TimeUnit.DAYS))
    dt3.addPredecessor(b3)

    dt4 = pf3.addTask()
    dt4.setName("Inspection & Signoff")
    dt4.setStart(LocalDateTime.of(2026, 3, 20, 8, 0))
    dt4.setDuration(Duration.getInstance(2, TimeUnit.DAYS))
    b4 = Relation.Builder()
    b4.successorTask(dt4).predecessorTask(dt3).type(RelationType.START_FINISH).lag(Duration.getInstance(0, TimeUnit.DAYS))
    dt4.addPredecessor(b4)

    m2 = pf3.addTask()
    m2.setName("Phase 1 Handover Milestone")
    m2.setMilestone(True)
    m2.setDuration(Duration.getInstance(0, TimeUnit.DAYS))
    b5 = Relation.Builder()
    b5.successorTask(m2).predecessorTask(dt4).type(RelationType.FINISH_START).lag(Duration.getInstance(0, TimeUnit.DAYS))
    m2.addPredecessor(b5)

    deps_path = os.path.join(output_dir, "test_dependencies.xml")
    writer.write(pf3, deps_path)

    # -------------------------------------------------------------
    # Test Case 5: Corrupted MPP file fixture
    # -------------------------------------------------------------
    corrupt_path = os.path.join(output_dir, "corrupted.mpp")
    with open(corrupt_path, "wb") as f:
        f.write(b"CORRUPTED_NON_MPP_BINARY_DATA_HEADER_1234567890\x00\xff\xfe\x00\x01\x02\x03")

    print(f"Generated test fixtures in '{output_dir}':")
    print(f" - {flat_path}")
    print(f" - {hier_path}")
    print(f" - {deps_path}")
    print(f" - {corrupt_path}")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    generate_all_fixtures(os.path.abspath(out))
