# Third party imports
from fastapi import Request
from fastapi.responses import JSONResponse

# Local imports
from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class AuthenticationHandler(BaseExceptionHandler):
    async def handle_authentication_error(self, request: Request, exc: AuthenticationFailedException):
        return JSONResponse(
            status_code=exc.status_code,
            content=self._create_base_response(request, exc, "authentication_error")
        ) 