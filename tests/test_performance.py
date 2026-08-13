import os
import time
import tracemalloc
import pytest

from mpp_parser.engine import parse_mpp_file
from mpp_parser.exporter import MPPExporter
from mpp_parser.schema import TaskModificationSchema

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def test_benchmark_small_project(tmp_path):
    """
    Performance Benchmark: 100 tasks (small_project.xml)
    Measures parse duration, export duration, memory usage, and dependency preservation.
    """
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "small_project.xml"))
    assert os.path.exists(filepath)

    tracemalloc.start()
    t0 = time.time()
    result = parse_mpp_file(filepath)
    parse_duration = time.time() - t0
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert result.taskCount == 100
    assert parse_duration < 2.0  # Should parse in under 2 seconds
    print(f"\n[Small Project 100 Tasks] Parse Time: {parse_duration:.3f}s | Peak Memory: {peak_mem / 1024 / 1024:.2f} MB")

    out_file = str(tmp_path / "exported_small.xml")
    exporter = MPPExporter()
    
    t1 = time.time()
    export_result = exporter.modify_and_export(filepath, out_file, [
        TaskModificationSchema(id="10", name="BENCHMARK UPDATED TASK")
    ])
    export_duration = time.time() - t1

    assert export_result.taskCount == 100
    assert export_result.exportVerified is True
    assert export_result.verification.dependenciesPreserved is True
    print(f"[Small Project 100 Tasks] Export Time: {export_duration:.3f}s")


def test_benchmark_medium_project(tmp_path):
    """
    Performance Benchmark: 5,000 tasks (medium_project.xml)
    Measures parse duration, export duration, and scale handling.
    """
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "medium_project.xml"))
    if not os.path.exists(filepath):
        pytest.skip("medium_project.xml fixture not found")

    tracemalloc.start()
    t0 = time.time()
    result = parse_mpp_file(filepath)
    parse_duration = time.time() - t0
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert result.taskCount == 5000
    assert parse_duration < 10.0  # Should parse 5000 tasks in under 10 seconds
    print(f"\n[Medium Project 5000 Tasks] Parse Time: {parse_duration:.3f}s | Peak Memory: {peak_mem / 1024 / 1024:.2f} MB")

    out_file = str(tmp_path / "exported_medium.xml")
    exporter = MPPExporter()
    
    t1 = time.time()
    export_result = exporter.modify_and_export(filepath, out_file, [])
    export_duration = time.time() - t1

    assert export_result.taskCount == 5000
    assert export_result.exportVerified is True
    print(f"[Medium Project 5000 Tasks] Export Time: {export_duration:.3f}s")


@pytest.mark.performance
def test_benchmark_large_project():
    """
    Performance Benchmark: 25,000 tasks (large_project.xml)
    Scalability stress test verifying high-volume parsing.
    """
    filepath = os.path.abspath(os.path.join(FIXTURES_DIR, "large_project.xml"))
    if not os.path.exists(filepath):
        pytest.skip("large_project.xml fixture not found")

    t0 = time.time()
    result = parse_mpp_file(filepath)
    parse_duration = time.time() - t0

    assert result.taskCount == 25000
    print(f"\n[Large Project 25000 Tasks] Parse Time: {parse_duration:.3f}s")
