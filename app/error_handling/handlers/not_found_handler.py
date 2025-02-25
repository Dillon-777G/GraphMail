from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

from app.error_handling.handlers.base_handler import BaseExceptionHandler

class NotFoundHandler(BaseExceptionHandler):
    async def handle_not_found(self, request: Request, exc: HTTPException):
        self._log_error(request, exc)
        
        response = self._create_base_response(request, exc, "not_found_error")
        if exc.status_code == 404:
            response.update({
                "available_endpoints": {
                    "auth": [
                        "/auth",
                        "/auth/callback"
                    ],
                    "attachments": [
                        "/attachments/{folder_id}/{message_id}",
                        "/attachments/{folder_id}/{message_id}/{attachment_id}/download"
                    ],
                    "folders": [
                        "/folders/root",
                        "/folders/{folder_id}/contents"
                    ],
                    "emails": [
                        "/emails/{folder_id}/select",
                        "/recursive_emails/folder/{folder_id}/all_emails"
                    ]
                },
                "method": request.method,
                "supported_methods": ["GET", "POST"]
            })

            if request.method not in ["GET", "POST"]:
                response["method_error"] = f"Method '{request.method}' not supported. Use GET or POST."

        return JSONResponse(status_code=exc.status_code, content=response) 