from fastapi import Request
from fastapi.responses import JSONResponse

from app.error_handling.exceptions.email_exception import EmailException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class EmailHandler(BaseExceptionHandler):
    async def handle_email_error(self, request: Request, exc: EmailException):
        self._log_error(request, exc, f"Folder ID: {exc.folder_id}, Email source ID: {exc.message_id}")
        response = self._create_base_response(request, exc, "email_error")
        response.update({
            "folder_name": exc.folder_name,
            "message_id": exc.message_id
        })
        return JSONResponse(status_code=exc.status_code, content=response) 