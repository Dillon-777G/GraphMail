# Third party imports
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import NoResultFound

# Local imports
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class NoResultHandler(BaseExceptionHandler):
    async def handle_no_result_found(self, request: Request, exc: NoResultFound):
        self._log_error(request, exc, "No result found in database")
        response = self._create_base_response(request, exc, "no_result_error")
        return JSONResponse(status_code=404, content=response) 