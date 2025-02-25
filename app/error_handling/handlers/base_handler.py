import logging
from typing import Dict, Any
from fastapi import Request

class BaseExceptionHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _create_base_response(self, request: Request, exc: Exception, error_type: str) -> Dict[str, Any]:
        """Creates the base response structure used by all handlers"""
        return {
            "status": "failed",
            "type": error_type,
            "detail": getattr(exc, 'detail', str(exc)),
            "path": str(request.url)
        }

    def _log_error(self, request: Request, exc: Exception, additional_info: str = ""):
        """Centralized error logging"""
        error_msg = f"Error on {request.url}: {getattr(exc, 'detail', str(exc))}"
        if additional_info:
            error_msg += f", {additional_info}"
        self.logger.error(error_msg) 