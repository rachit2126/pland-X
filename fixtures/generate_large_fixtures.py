import os
import xml.etree.ElementTree as ET


def generate_mspdi_xml(filepath: str, task_count: int, project_name: str = "Benchmark Project"):
    """
    Generates a valid MSPDI XML project file with task_count tasks, hierarchy, and predecessors.
    """
    project = ET.Element("Project", xmlns="http://schemas.microsoft.com/project")
    
    name_elem = ET.SubElement(project, "Name")
    name_elem.text = project_name
    
    cal_elem = ET.SubElement(project, "CalendarUID")
    cal_elem.text = "1"

    start_elem = ET.SubElement(project, "StartDate")
    start_elem.text = "2026-01-01T08:00:00"

    tasks_elem = ET.SubElement(project, "Tasks")

    for i in range(1, task_count + 1):
        t_elem = ET.SubElement(tasks_elem, "Task")
        
        uid = ET.SubElement(t_elem, "UID")
        uid.text = str(i)
        
        tid = ET.SubElement(t_elem, "ID")
        tid.text = str(i)
        
        is_summary = (i % 20 == 1)
        is_milestone = (i % 20 == 0)

        t_name = ET.SubElement(t_elem, "Name")
        if is_summary:
            t_name.text = f"Summary Group {i // 20 + 1}"
        elif is_milestone:
            t_name.text = f"Milestone Gate {i}"
        else:
            t_name.text = f"Construction Task {i}"

        outline_level = 1 if is_summary else 2
        ol_elem = ET.SubElement(t_elem, "OutlineLevel")
        ol_elem.text = str(outline_level)

        wbs_elem = ET.SubElement(t_elem, "WBS")
        wbs_elem.text = str(i)

        dur_elem = ET.SubElement(t_elem, "Duration")
        dur_elem.text = "PT0H0M0S" if is_milestone else "PT40H0M0S"

        pct_elem = ET.SubElement(t_elem, "PercentComplete")
        pct_elem.text = "100" if is_milestone else str((i * 7) % 100)

        # Predecessor link every 3rd task
        if i > 1 and not is_summary:
            pred_elem = ET.SubElement(t_elem, "PredecessorLink")
            p_uid = ET.SubElement(pred_elem, "PredecessorUID")
            p_uid.text = str(i - 1)
            p_type = ET.SubElement(pred_elem, "Type")
            p_type.text = "1"  # Finish-to-Start (FS)

    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    tree = ET.ElementTree(project)
    ET.indent(tree, space="  ", level=0)
    tree.write(filepath, encoding="utf-8", xml_declaration=True)
    print(f"Generated MSPDI XML fixture with {task_count} tasks: '{filepath}'")


def main():
    fixtures_dir = os.path.dirname(os.path.abspath(__file__))
    generate_mspdi_xml(os.path.join(fixtures_dir, "small_project.xml"), 100, "Small Project (100 tasks)")
    generate_mspdi_xml(os.path.join(fixtures_dir, "medium_project.xml"), 5000, "Medium Project (5000 tasks)")
    generate_mspdi_xml(os.path.join(fixtures_dir, "large_project.xml"), 25000, "Large Project (25000 tasks)")


if __name__ == "__main__":
    main()
