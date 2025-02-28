# Third party imports
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Local imports
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class ValidationHandler(BaseExceptionHandler):
    async def handle_validation_error(self, request: Request, exc: RequestValidationError):
        self._log_error(request, exc)
        
        response = self._create_base_response(request, exc, "validation_error")
        response["errors"] = [
            {
                "location": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            }
            for error in exc.errors()
        ]
        
        return JSONResponse(
            status_code=422,
            content=response
        ) 