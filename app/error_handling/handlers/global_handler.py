import traceback
from fastapi import Request
from fastapi.responses import JSONResponse

from app.error_handling.handlers.base_handler import BaseExceptionHandler

class GlobalHandler(BaseExceptionHandler):
    async def handle_global_error(self, request: Request, exc: Exception):
        stack_trace = traceback.format_exc()
        self.logger.error(
            "Unhandled exception on %s\nError: %s\nStack trace:\n%s",
            request.url, str(exc), stack_trace
        )
        return JSONResponse(
            status_code=500,
            content=self._create_base_response(
                request, 
                Exception("An unexpected error occurred. Please try again later."),
                "internal_server_error"
            )
        ) 