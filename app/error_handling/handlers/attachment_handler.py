# Third party imports
from fastapi import Request
from fastapi.responses import JSONResponse

# Local imports
from app.error_handling.exceptions.email_attachment_exception import EmailAttachmentException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class AttachmentHandler(BaseExceptionHandler):
    async def handle_attachment_error(self, request: Request, exc: EmailAttachmentException):
        self._log_error(request, exc, f"Attachment ID: {exc.attachment_id}")
        response = self._create_base_response(request, exc, "attachment_error")
        response["attachment_id"] = exc.attachment_id
        return JSONResponse(status_code=exc.status_code, content=response) 