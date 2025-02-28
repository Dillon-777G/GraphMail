# Third party imports
from fastapi import Request
from fastapi.responses import JSONResponse

# Local imports
from app.error_handling.exceptions.id_translation_exception import IdTranslationException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class IdTranslationHandler(BaseExceptionHandler):
    async def handle_id_translation_error(self, request: Request, exc: IdTranslationException):
        self._log_error(request, exc, f"Source IDs: {exc.source_ids}")
        response = self._create_base_response(request, exc, "id_translation_error")
        response["source_ids"] = exc.source_ids
        return JSONResponse(status_code=exc.status_code, content=response) 