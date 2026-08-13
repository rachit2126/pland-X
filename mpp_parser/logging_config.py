import logging
import sys
from .config import settings
from .middleware import CorrelationIdFilter


def setup_logging():
    """Configures structured ISO-timestamped logging with correlation IDs for the service."""
    log_format = "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
    date_format = "%Y-%m-%dT%H:%M:%SZ"

    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    handler.addFilter(CorrelationIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Avoid duplicate handlers if re-initialized
    root_logger.handlers = [handler]

    logger = logging.getLogger("mpp_parser")
    logger.setLevel(log_level)
    return logger
