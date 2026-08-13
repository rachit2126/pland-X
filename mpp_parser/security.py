import os
import re
import logging
from typing import Optional, Set
from fastapi import status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES: Set[str] = {
    "application/vnd.ms-project",
    "application/msprops",
    "application/x-project",
    "application/xml",
    "text/xml",
    "application/octet-stream",
}


def sanitize_filename(filename: str) -> str:
    """
    Strips directory traversal vectors, null bytes, and unsafe characters from filenames.
    """
    if not filename:
        return "unnamed.mpp"
    
    # Normalize Windows backslashes to forward slashes first
    clean_name = filename.replace("\\", "/").strip()
    # Take basename to strip directory paths
    clean_name = os.path.basename(clean_name)
    # Remove null bytes
    clean_name = clean_name.replace("\x00", "")
    # Replace unsafe characters
    clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", clean_name)
    
    if not clean_name:
        return "unnamed.mpp"
    return clean_name


def validate_mime_type(content_type: Optional[str]) -> Optional[JSONResponse]:
    """
    Validates uploaded Content-Type header against allowed MIME set.
    """
    if not content_type:
        return None  # Default fallback if header not provided

    clean_mime = content_type.split(";")[0].strip().lower()
    if clean_mime not in ALLOWED_MIME_TYPES:
        allowed_str = ", ".join(sorted(ALLOWED_MIME_TYPES))
        logger.warning(f"Rejected upload with unsupported MIME type '{clean_mime}'")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": f"Unsupported MIME type '{clean_mime}'. Allowed MIME types: {allowed_str}"},
        )
    return None
