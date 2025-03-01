# Third party imports
from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.error_handling.handlers.base_handler import BaseExceptionHandler

class ApiNotFoundHandler(BaseExceptionHandler):
    async def handle_api_not_found(self, request: Request, exc: HTTPException):
        self._log_error(request, exc)
        
        response = self._create_base_response(request, exc, "api_not_found_error")
        if exc.status_code == 404:
            response.update({
                "available_endpoints": {
                    "auth": [
                        "/auth",
                        "/auth/callback"
                    ],
                    "attachments": [
                        "GET /attachments/{folder_id}/{message_id}",
                        "POST /attachments/{folder_id}/{message_id}/{attachment_id}/download"
                    ],
                    "folders": [
                        "GET /folders/root",
                        "GET /folders/{folder_id}/contents"
                    ],
                    "emails": [
                        "POST /emails/{folder_id}/select",
                        "POST /recursive_emails/folder/{folder_id}/all_emails"
                    ]
                },
                "method": request.method,
                "supported_methods": ["GET", "POST"]
            })

            if request.method not in ["GET", "POST"]:
                response["method_error"] = f"Method '{request.method}' not supported. Use GET or POST."

        return JSONResponse(status_code=exc.status_code, content=response) 