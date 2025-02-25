from fastapi import Request
from fastapi.responses import JSONResponse

from app.error_handling.exceptions.attachment_persistence_exception import AttachmentPersistenceException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class AttachmentPersistenceHandler(BaseExceptionHandler):
    async def handle_attachment_persistence_error(self, request: Request, exc: AttachmentPersistenceException):
        # Build error context
        error_context = []
        if exc.attachment:
            error_context.append(f"Attachment ID: {exc.attachment.graph_attachment_id}")
        if exc.original_error:
            error_context.append(f"Original error: {str(exc.original_error)}")
        
        self._log_error(request, exc, ", ".join(error_context))
        
        # Build response
        response = self._create_base_response(request, exc, "attachment_persistence_error")
        if exc.attachment:
            response["attachment"] = {
                "id": exc.attachment.graph_attachment_id,
                "name": exc.attachment.name,
                "email_id": exc.attachment.email_id
            }
        
        if exc.original_error:
            response["error_details"] = str(exc.original_error)
            
        return JSONResponse(status_code=exc.status_code, content=response) 