import os
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

from ..security import sanitize_filename, validate_mime_type
from ..config import settings
from ..engine import parse_mpp_file
from .models import PlanDProject, SyncResponse, DashboardMetrics
from .repository import programme_service

logger = logging.getLogger(__name__)

plandx_router = APIRouter(prefix="/api/v1/projects", tags=["PlanD-X Programme Control"])


@plandx_router.get(
    "/{project_id}/programme",
    response_model=PlanDProject,
    responses={
        200: {"description": "PlanD-X Programme Data", "model": PlanDProject},
        404: {"description": "Project not found"},
    },
)
def get_project_programme(project_id: str):
    """
    Returns imported and normalized PlanD-X programme data for specified project ID.
    """
    programme = programme_service.get_programme(project_id)
    if not programme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project programme '{project_id}' not found. Please sync an MPP file first.",
        )
    return programme


@plandx_router.post(
    "/{project_id}/sync",
    response_model=SyncResponse,
    responses={
        200: {"description": "Successfully synced programme data", "model": SyncResponse},
        422: {"description": "Corrupted or invalid file"},
    },
)
async def sync_project_mpp(project_id: str, file: UploadFile = File(...)):
    """
    Parses uploaded MPP file and syncs extracted activities, dependencies, resources,
    BOQ references, and progress metrics into PlanD-X project structure.
    """
    if not file.filename:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Unable to sync project: No file provided"},
        )

    clean_filename = sanitize_filename(file.filename)

    ext = os.path.splitext(clean_filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": f"Unsupported file format '{ext}'"},
        )

    mime_err = validate_mime_type(file.content_type)
    if mime_err:
        return mime_err

    contents = await file.read()
    if not contents:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "Unable to sync project: Empty file"},
        )

    tmp_path = None
    try:
        suffix = os.path.splitext(clean_filename)[1] or ".mpp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        mpp_result = parse_mpp_file(tmp_path, source_filename=clean_filename)
        sync_result = programme_service.sync_mpp_data(project_id, mpp_result)
        return sync_result

    except Exception as e:
        logger.error(f"Error syncing project '{project_id}': {e}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": f"Unable to sync project programme: {e}"},
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@plandx_router.get(
    "/{project_id}/dashboard",
    response_model=DashboardMetrics,
    responses={
        200: {"description": "Programme Dashboard Telemetry", "model": DashboardMetrics},
    },
)
def get_project_dashboard(project_id: str):
    """
    Returns dashboard-ready programme telemetry (overall progress, delays, critical activities, milestones).
    """
    return programme_service.get_dashboard_metrics(project_id)
