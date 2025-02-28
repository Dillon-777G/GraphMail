# Third party imports
from fastapi import Request
from fastapi.responses import JSONResponse
from kiota_abstractions.api_error import APIError

from app.error_handling.handlers.base_handler import BaseExceptionHandler

class APIErrorHandler(BaseExceptionHandler):

    async def handle_api_error(self, request: Request, exc: APIError):
        # Use the APIError attributes directly.
        error_message = exc.message or "Unknown error"
        status_code = exc.response_status_code or 500
        error_code = None

        # If additional error details are provided, use them.
        if hasattr(exc, 'error') and exc.error:
            if hasattr(exc.error, 'message') and exc.error.message:
                error_message = exc.error.message
            if hasattr(exc.error, 'code') and exc.error.code:
                error_code = exc.error.code

        self._log_error(request, exc, f"API Error: {status_code}")

        # Build the response using the APIError's message as detail.
        response = self._create_base_response(request, exc, "graph_api_error")
        response["status_code"] = status_code
        response["error_code"] = error_code
        response["detail"] = error_message

        return JSONResponse(status_code=status_code, content=response)
