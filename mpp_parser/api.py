import os
import tempfile
import time
import json
from typing import Optional, List
from fastapi import FastAPI, APIRouter, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .logging_config import setup_logging
from .middleware import CorrelationIdMiddleware
from .security import sanitize_filename, validate_mime_type
from .metrics import (
    get_metrics_response,
    MPP_PARSE_TOTAL,
    MPP_EXPORT_TOTAL,
    MPP_EXPORT_FAILURES_TOTAL,
    MPP_PROCESSING_SECONDS,
    MPP_UPLOADED_BYTES,
    MPP_TASKS_PROCESSED,
)
from .engine import parse_mpp_file
from .exporter import MPPExporter
from .schema import (
    MPPParseResultSchema,
    ErrorResponseSchema,
    TaskModificationSchema,
)

logger = setup_logging()

app = FastAPI(
    title="MPP Import Parser Service",
    description="Standalone Python Service parsing Microsoft Project (.MPP) files to structured JSON and exporting updated programmes.",
    version="1.1.0",
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

v1_router = APIRouter(prefix="/api/v1")


def _validate_file_extension(filename: str):
    """Validates file extension against allowed settings."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        allowed_str = ", ".join(sorted(settings.ALLOWED_EXTENSIONS))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": f"Unsupported file format '{ext}'. Supported formats: {allowed_str}"},
        )
    return None


async def _read_file_contents_safely(file: UploadFile):
    """Reads uploaded file contents in chunks enforcing max size limit."""
    contents = bytearray()
    chunk_size = 1024 * 1024
    max_bytes = settings.max_upload_size_bytes

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        contents.extend(chunk)
        if len(contents) > max_bytes:
            return None, JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"error": f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB"},
            )

    if not contents or len(contents) == 0:
        return None, JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Unable to parse MPP file: Empty file"},
        )

    return bytes(contents), None


@v1_router.get("/health")
@app.get("/health", include_in_schema=False)
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "mpp-parser-service", "version": "1.1.0"}


@v1_router.get("/metrics")
@app.get("/metrics", include_in_schema=False)
def metrics_endpoint():
    """Exposes Prometheus telemetry metrics."""
    return get_metrics_response()


EXAMPLE_MODIFICATIONS = '[\n  {\n    "taskId": "25",\n    "name": "Updated Task",\n    "durationDays": 20,\n    "percentComplete": 50\n  }\n]'


@v1_router.post(
    "/parse",
    response_model=MPPParseResultSchema,
    responses={
        200: {"description": "Successfully parsed MPP file", "model": MPPParseResultSchema},
        413: {"description": "File payload exceeds max size limit", "model": ErrorResponseSchema},
        422: {"description": "Corrupted or unparseable MPP file", "model": ErrorResponseSchema},
    },
)
@app.post("/parse", response_model=MPPParseResultSchema, include_in_schema=False)
async def parse_mpp(file: UploadFile = File(...)):
    """
    Accepts multipart/form-data (.MPP file upload) and returns structured JSON output.
    Returns 422 Unprocessable Entity if file cannot be parsed or has invalid format.
    Returns 413 Payload Too Large if file size exceeds maximum configured threshold.
    """
    start_time = time.time()
    if not file.filename:
        MPP_PARSE_TOTAL.labels(status="failure").inc()
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Unable to parse MPP file: No file provided"},
        )

    clean_filename = sanitize_filename(file.filename)

    ext_err = _validate_file_extension(clean_filename)
    if ext_err:
        MPP_PARSE_TOTAL.labels(status="failure").inc()
        return ext_err

    mime_err = validate_mime_type(file.content_type)
    if mime_err:
        MPP_PARSE_TOTAL.labels(status="failure").inc()
        return mime_err

    contents, err_resp = await _read_file_contents_safely(file)
    if err_resp:
        MPP_PARSE_TOTAL.labels(status="failure").inc()
        return err_resp

    file_bytes_len = len(contents)
    MPP_UPLOADED_BYTES.labels(operation="parse").inc(file_bytes_len)

    tmp_path = None
    try:
        suffix = os.path.splitext(clean_filename)[1] or ".mpp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        result = parse_mpp_file(tmp_path, source_filename=clean_filename)
        
        duration = time.time() - start_time
        MPP_PROCESSING_SECONDS.labels(operation="parse").observe(duration)
        MPP_PARSE_TOTAL.labels(status="success").inc()
        MPP_TASKS_PROCESSED.labels(operation="parse").inc(result.taskCount)

        logger.info(
            f"Parsed file '{clean_filename}' ({file_bytes_len} bytes) "
            f"tasks={result.taskCount} in {duration:.3f}s"
        )
        return result

    except Exception as e:
        MPP_PARSE_TOTAL.labels(status="failure").inc()
        logger.error(f"Error parsing uploaded file '{clean_filename}': {e}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Unable to parse MPP file"},
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@v1_router.post(
    "/export",
    response_model=MPPParseResultSchema,
    responses={
        200: {"description": "Successfully modified and exported project file", "model": MPPParseResultSchema},
        413: {"description": "File payload exceeds max size limit", "model": ErrorResponseSchema},
        422: {"description": "Error modifying or exporting project file", "model": ErrorResponseSchema},
    },
)
@app.post("/export", response_model=MPPParseResultSchema, include_in_schema=False)
async def export_mpp(
    file: UploadFile = File(...),
    modifications_json: Optional[str] = Form(
        default=None,
        description="Optional JSON array of task modifications. Supports task name, dates, duration, percent complete, and dependencies.",
        openapi_examples={
            "default": {
                "summary": "Example Task Modifications Array",
                "value": EXAMPLE_MODIFICATIONS,
            }
        },
    )
):
    """
    Accepts multipart upload (.MPP file) and optional JSON modifications string.
    Modifies tasks, exports updated MSPDI XML file, and returns validated result.
    """
    start_time = time.time()
    if not file.filename:
        MPP_EXPORT_TOTAL.labels(status="failure").inc()
        MPP_EXPORT_FAILURES_TOTAL.inc()
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Unable to parse MPP file: No file provided"},
        )

    clean_filename = sanitize_filename(file.filename)

    ext_err = _validate_file_extension(clean_filename)
    if ext_err:
        MPP_EXPORT_TOTAL.labels(status="failure").inc()
        MPP_EXPORT_FAILURES_TOTAL.inc()
        return ext_err

    mime_err = validate_mime_type(file.content_type)
    if mime_err:
        MPP_EXPORT_TOTAL.labels(status="failure").inc()
        MPP_EXPORT_FAILURES_TOTAL.inc()
        return mime_err

    contents, err_resp = await _read_file_contents_safely(file)
    if err_resp:
        MPP_EXPORT_TOTAL.labels(status="failure").inc()
        MPP_EXPORT_FAILURES_TOTAL.inc()
        return err_resp

    file_bytes_len = len(contents)
    MPP_UPLOADED_BYTES.labels(operation="export").inc(file_bytes_len)

    tmp_in = None
    tmp_out = None
    try:
        suffix = os.path.splitext(clean_filename)[1] or ".mpp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_in = tmp.name

        # Parse modifications safely
        mods: List[TaskModificationSchema] = []
        if modifications_json is not None:
            s = str(modifications_json).strip()
            if s and s != "string":
                try:
                    raw_mods = json.loads(s)
                    if isinstance(raw_mods, list):
                        mods = [TaskModificationSchema(**m) for m in raw_mods]
                    elif isinstance(raw_mods, dict):
                        mods = [TaskModificationSchema(**raw_mods)]
                except json.JSONDecodeError:
                    MPP_EXPORT_TOTAL.labels(status="failure").inc()
                    MPP_EXPORT_FAILURES_TOTAL.inc()
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"error": "Invalid JSON format in modifications_json"},
                    )
                except Exception as val_err:
                    MPP_EXPORT_TOTAL.labels(status="failure").inc()
                    MPP_EXPORT_FAILURES_TOTAL.inc()
                    return JSONResponse(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        content={"error": f"Invalid JSON format in modifications_json: {val_err}"},
                    )

        tmp_out = tmp_in + "_exported.xml"
        exporter = MPPExporter()
        result = exporter.modify_and_export(tmp_in, tmp_out, mods)

        duration = time.time() - start_time
        MPP_PROCESSING_SECONDS.labels(operation="export").observe(duration)
        MPP_EXPORT_TOTAL.labels(status="success").inc()
        MPP_TASKS_PROCESSED.labels(operation="export").inc(result.taskCount)

        logger.info(
            f"Exported file '{clean_filename}' ({file_bytes_len} bytes) "
            f"tasks={result.taskCount} in {duration:.3f}s"
        )
        return result

    except Exception as e:
        MPP_EXPORT_TOTAL.labels(status="failure").inc()
        MPP_EXPORT_FAILURES_TOTAL.inc()
        logger.error(f"Error exporting file '{clean_filename}': {e}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": f"Unable to export MPP file: {e}"},
        )
    finally:
        for p in (tmp_in, tmp_out):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


from .plandx.router import plandx_router

# Include API v1 Router & PlanD-X Integration Router
app.include_router(v1_router)
app.include_router(plandx_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
