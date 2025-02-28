# FastAPI imports
from fastapi import Request
from fastapi.responses import JSONResponse

# Local imports
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class ValueErrorHandler(BaseExceptionHandler):
    async def handle_value_error(self, request: Request, exc: ValueError):
        self._log_error(request, exc)
        response = self._create_base_response(request, exc, "value_error")
        return JSONResponse(status_code=400, content=response) 