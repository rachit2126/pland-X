import os
from typing import Set


class Settings:
    """Central configuration settings for the MPP Parser Service."""

    def __init__(self):
        self.MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
        
        ext_env = os.getenv("ALLOWED_EXTENSIONS", ".mpp,.xml,.mpx,.mpt")
        self.ALLOWED_EXTENSIONS: Set[str] = {
            e.strip().lower() for e in ext_env.split(",") if e.strip()
        }
        
        self.HOST: str = os.getenv("HOST", "0.0.0.0")
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
