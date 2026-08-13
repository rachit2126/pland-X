from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import Response

# Prometheus Metrics Definitions
MPP_PARSE_TOTAL = Counter(
    "mpp_parse_total",
    "Total number of MPP parse operations",
    ["status"]
)

MPP_EXPORT_TOTAL = Counter(
    "mpp_export_total",
    "Total number of MPP export operations",
    ["status"]
)

MPP_EXPORT_FAILURES_TOTAL = Counter(
    "mpp_export_failures_total",
    "Total number of MPP export failures"
)

MPP_PROCESSING_SECONDS = Histogram(
    "mpp_processing_seconds",
    "Processing time in seconds",
    ["operation"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

MPP_UPLOADED_BYTES = Counter(
    "mpp_uploaded_bytes",
    "Total bytes of uploaded project files",
    ["operation"]
)

MPP_TASKS_PROCESSED = Counter(
    "mpp_tasks_processed",
    "Total task records processed across operations",
    ["operation"]
)


def get_metrics_response() -> Response:
    """Returns standard Prometheus metrics exposition payload."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
