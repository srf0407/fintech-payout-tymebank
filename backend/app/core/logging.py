import logging
import structlog
import uuid
import sys
from contextvars import ContextVar
from typing import Optional
from .config import settings

correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

def configure_logging() -> None:
    """Configure structured logging with correlation ID support"""
    
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level
    )

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger_obj = logging.getLogger(name)
        logger_obj.handlers = []
        logger_obj.propagate = True
        logger_obj.setLevel(level)
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_correlation_id,
            structlog.dev.ConsoleRenderer() if settings.debug else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to every log entry"""
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict

def get_correlation_id() -> str:
    """Get current correlation ID or generate new one"""
    correlation_id = correlation_id_var.get()
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        correlation_id_var.set(correlation_id)
    return correlation_id

def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context"""
    correlation_id_var.set(correlation_id)

logger = structlog.get_logger()

def get_logger(name: str = None):
    """Get a logger instance with optional name"""
    if name:
        return structlog.get_logger(name)
    return logger