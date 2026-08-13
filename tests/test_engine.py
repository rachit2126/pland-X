import os
import pytest
from mpp_parser.engine import MPPParser, parse_mpp_file, _map_relation_type, _format_date

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_engine_date_formatter():
    """Verify _format_date helper."""
    assert _format_date("2026-08-14T08:00") == "2026-08-14"
    assert _format_date("2026-08-14 17:00:00") == "2026-08-14"
    assert _format_date("2026-08-14") == "2026-08-14"
    assert _format_date(None) is None


def test_engine_relation_type_mapper():
    """Verify relation type mapping logic."""
    assert _map_relation_type("FINISH_START") == "FS"
    assert _map_relation_type("START_START") == "SS"
    assert _map_relation_type("FINISH_FINISH") == "FF"
    assert _map_relation_type("START_FINISH") == "SF"


def test_engine_nonexistent_file_raises():
    """Verify FileNotFoundError raised for missing file."""
    with pytest.raises(FileNotFoundError):
        parse_mpp_file("/nonexistent/file/path.mpp")


def test_engine_corrupted_file_raises():
    """Verify ValueError raised for corrupted binary file."""
    corrupt_path = os.path.abspath(os.path.join(FIXTURES_DIR, "corrupted.mpp"))
    with pytest.raises(ValueError) as exc_info:
        parse_mpp_file(corrupt_path)
    assert "Unable to parse MPP file" in str(exc_info.value)
