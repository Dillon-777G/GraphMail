from fastapi import Request
from fastapi.responses import JSONResponse

from app.error_handling.exceptions.db_email_recipient_exception import DBEmailRecipientException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class DBEmailRecipientHandler(BaseExceptionHandler):
    async def handle_db_email_recipient_error(self, request: Request, exc: DBEmailRecipientException):
        # Build error context for logging
        error_context = []
        if exc.email_id:
            error_context.append(f"Email ID: {exc.email_id}")
        if exc.recipient_addresses:
            addresses_str = ", ".join(exc.recipient_addresses[:5])
            if len(exc.recipient_addresses) > 5:
                addresses_str += f"... and {len(exc.recipient_addresses) - 5} more"
            error_context.append(f"Recipients: {addresses_str}")
        
        self._log_error(request, exc, ", ".join(error_context))
        
        # Build response
        response = self._create_base_response(request, exc, "db_email_recipient_error")
        if exc.email_id:
            response["email_id"] = exc.email_id
        if exc.recipient_addresses:
            response["recipient_addresses"] = exc.recipient_addresses[:10]  # Limit to first 10 for response size
            if len(exc.recipient_addresses) > 10:
                response["additional_recipients_count"] = len(exc.recipient_addresses) - 10
        
        return JSONResponse(status_code=exc.status_code, content=response) 