from fastapi import Request
from fastapi.responses import JSONResponse

from app.error_handling.exceptions.recursive_email_exception import RecursiveEmailException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class RecursiveEmailHandler(BaseExceptionHandler):
    async def handle_recursive_email_error(self, request: Request, exc: RecursiveEmailException):
        self._log_error(request, exc, f"Folder ID: {exc.folder_id}")
        response = self._create_base_response(request, exc, "recursive_email_error")
        response["folder_id"] = exc.folder_id
        return JSONResponse(status_code=exc.status_code, content=response) 