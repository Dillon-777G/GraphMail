# FastAPI imports
from fastapi import Request
from fastapi.responses import JSONResponse

# Local imports
from app.error_handling.exceptions.folder_exception import FolderException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class FolderHandler(BaseExceptionHandler):
    async def handle_folder_error(self, request: Request, exc: FolderException):
        self._log_error(request, exc)
        response = self._create_base_response(request, exc, "folder_error")
        if exc.folder_name:
            response["folder_name"] = exc.folder_name
        if exc.folder_id:
            response["folder_id"] = exc.folder_id
        return JSONResponse(status_code=exc.status_code, content=response) 