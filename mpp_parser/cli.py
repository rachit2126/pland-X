import sys
import os
import json
import argparse

from .engine import parse_mpp_file
from .exporter import MPPExporter
from .schema import ErrorResponseSchema, TaskModificationSchema


def main():
    """CLI tool for parsing MPP files to JSON: mpp-parse input.mpp"""
    parser = argparse.ArgumentParser(
        prog="mpp-parse",
        description="Extract structured programme JSON from Microsoft Project (.MPP) files."
    )
    parser.add_argument("input_file", help="Path to input Microsoft Project (.MPP) file")
    parser.add_argument("-o", "--output", help="Optional output JSON file path (defaults to stdout)")
    parser.add_argument("--pretty", action="store_true", help="Format JSON with 2-space indentation")
    
    args = parser.parse_args()

    input_path = args.input_file
    if not os.path.exists(input_path):
        err_json = ErrorResponseSchema(error=f"Unable to parse MPP file: File not found '{input_path}'").model_dump_json(indent=2 if args.pretty else None)
        sys.stderr.write(err_json + "\n")
        sys.exit(1)

    try:
        result = parse_mpp_file(input_path)
        indent = 2 if args.pretty else None
        output_json = result.model_dump_json(indent=indent)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json + "\n")
        else:
            sys.stdout.write(output_json + "\n")
        sys.exit(0)

    except Exception as e:
        err_json = ErrorResponseSchema(error=f"Unable to parse MPP file: {e}").model_dump_json(indent=2 if args.pretty else None)
        sys.stderr.write(err_json + "\n")
        sys.exit(1)


def main_export():
    """CLI tool for modifying and exporting project files: mpp-export input.mpp output.xml [--modify modifications.json]"""
    parser = argparse.ArgumentParser(
        prog="mpp-export",
        description="Modify project tasks and export updated MS Project compatible XML file."
    )
    parser.add_argument("input_file", help="Path to input Microsoft Project (.MPP/.XML) file")
    parser.add_argument("output_file", nargs="?", help="Output exported XML file path")
    parser.add_argument("-o", "--output", help="Output exported XML file path (alternative flag)")
    parser.add_argument("-m", "--modify", "--modifications", help="Optional JSON file containing list of task modifications")
    parser.add_argument("--json", action="store_true", help="Output full JSON result payload")
    parser.add_argument("--pretty", action="store_true", help="Format JSON output with 2-space indentation")

    args = parser.parse_args()

    input_path = args.input_file
    output_path = args.output_file or args.output

    if not output_path:
        sys.stderr.write("Error: Output file path is required. Usage: mpp-export input.mpp output.xml [--modify mods.json]\n")
        sys.exit(1)

    if not os.path.exists(input_path):
        sys.stderr.write(f"Error: Input file not found '{input_path}'\n")
        sys.exit(1)

    mods = []
    mod_param = args.modify
    if mod_param:
        if not os.path.exists(mod_param):
            sys.stderr.write(f"Error: Modifications JSON file not found '{mod_param}'\n")
            sys.exit(1)
        with open(mod_param, "r", encoding="utf-8") as f:
            raw_mods = json.load(f)
            if isinstance(raw_mods, list):
                mods = [TaskModificationSchema(**m) for m in raw_mods]
            elif isinstance(raw_mods, dict):
                mods = [TaskModificationSchema(**raw_mods)]

    try:
        exporter = MPPExporter()
        result = exporter.modify_and_export(input_path, output_path, mods)

        if args.json or args.pretty:
            sys.stdout.write(result.model_dump_json(indent=2 if args.pretty else None) + "\n")
        else:
            ver_status = "PASSED" if result.exportVerified else "FAILED"
            fmt_str = result.exportFormat or "MSPDI XML"
            sys.stdout.write("Export successful\n\n")
            sys.stdout.write(f"Format:\n{fmt_str}\n\n")
            sys.stdout.write(f"Tasks:\n{result.taskCount}\n\n")
            sys.stdout.write(f"Verification:\n{ver_status}\n")

        sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"Error exporting project file: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
