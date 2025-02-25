from fastapi import Request
from fastapi.responses import JSONResponse

from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class EmailPersistenceHandler(BaseExceptionHandler):
    async def handle_email_persistence_error(self, request: Request, exc: EmailPersistenceException):
        error_context = f"Message IDs: {exc.message_ids}"
        if exc.original_error:
            error_context += f", Original error: {str(exc.original_error)}"
        
        self._log_error(request, exc, error_context)
        
        response = self._create_base_response(request, exc, "email_persistence_error")
        if exc.message_ids:
            response["message_ids"] = exc.message_ids
        
        if exc.is_duplicate_error():
            response["error_type"] = "duplicate_entry"
        
        return JSONResponse(status_code=exc.status_code, content=response) 