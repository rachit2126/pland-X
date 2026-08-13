import os
import sys
import pytest
from unittest.mock import patch
from mpp_parser.cli import main, main_export

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_cli_mpp_parse(capsys):
    """Verify mpp-parse CLI command."""
    flat_path = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    test_args = ["mpp-parse", flat_path, "--pretty"]

    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Site Setup" in captured.out
    assert "Excavation Work" in captured.out


def test_cli_mpp_export(capsys, tmp_path):
    """Verify mpp-export CLI command with summary output."""
    flat_path = os.path.abspath(os.path.join(FIXTURES_DIR, "test_flat.xml"))
    out_xml = str(tmp_path / "cli_exported.xml")

    test_args = ["mpp-export", flat_path, out_xml]

    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exc_info:
            main_export()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()

    assert "Export successful" in captured.out
    assert "Format:" in captured.out
    assert "MSPDI XML" in captured.out
    assert "Verification:" in captured.out
    assert "PASSED" in captured.out
