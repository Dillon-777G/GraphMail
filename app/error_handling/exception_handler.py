import logging
import traceback
from typing import Dict, Any

from fastapi import Request
from fastapi.responses import JSONResponse

from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException
from app.error_handling.exceptions.email_exception import EmailException
from app.error_handling.exceptions.email_attachment_exception import EmailAttachmentException
from app.error_handling.exceptions.id_translation_exception import IdTranslationException
from app.error_handling.exceptions.folder_exception import FolderException
from app.error_handling.exceptions.graph_response_exception import GraphResponseException
from app.error_handling.exceptions.recursive_email_exception import RecursiveEmailException
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException

class ExceptionHandler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _create_base_response(self, request: Request, exc: Exception, error_type: str) -> Dict[str, Any]:
        """Creates the base response structure used by all handlers"""
        return {
            "status": "failed",
            "type": error_type,
            "detail": getattr(exc, 'detail', str(exc)),
            "path": str(request.url)
        }

    def _log_error(self, request: Request, exc: Exception, additional_info: str = ""):
        """Centralized error logging"""
        error_msg = f"Error on {request.url}: {getattr(exc, 'detail', str(exc))}"
        if additional_info:
            error_msg += f", {additional_info}"
        self.logger.error(error_msg)

    async def handle_authentication_error(self, request: Request, exc: AuthenticationFailedException):
        return JSONResponse(
            status_code=exc.status_code,
            content=self._create_base_response(request, exc, "authentication_error")
        )

    async def handle_email_error(self, request: Request, exc: EmailException):
        self._log_error(request, exc, f"Folder ID: {exc.folder_id}, Email source ID: {exc.message_id}")
        response = self._create_base_response(request, exc, "email_error")
        response.update({
            "folder_name": exc.folder_name,
            "message_id": exc.message_id
        })
        return JSONResponse(status_code=exc.status_code, content=response)

    async def handle_attachment_error(self, request: Request, exc: EmailAttachmentException):
        self._log_error(request, exc, f"Attachment ID: {exc.attachment_id}")
        response = self._create_base_response(request, exc, "attachment_error")
        response["attachment_id"] = exc.attachment_id
        return JSONResponse(status_code=exc.status_code, content=response)

    async def handle_id_translation_error(self, request: Request, exc: IdTranslationException):
        self._log_error(request, exc, f"Source IDs: {exc.source_ids}")
        response = self._create_base_response(request, exc, "id_translation_error")
        response["source_ids"] = exc.source_ids
        return JSONResponse(status_code=exc.status_code, content=response)

    async def handle_folder_error(self, request: Request, exc: FolderException):
        self._log_error(request, exc)
        response = self._create_base_response(request, exc, "folder_error")
        if exc.folder_name:
            response["folder_name"] = exc.folder_name
        if exc.folder_id:
            response["folder_id"] = exc.folder_id
        return JSONResponse(status_code=exc.status_code, content=response)

    async def handle_graph_response_error(self, request: Request, exc: GraphResponseException):
        self._log_error(request, exc)
        response = self._create_base_response(request, exc, "graph_response_error")
        response["response_type"] = exc.response_type
        return JSONResponse(status_code=exc.status_code, content=response)

    async def handle_recursive_email_error(self, request: Request, exc: RecursiveEmailException):
        self._log_error(request, exc, f"Folder ID: {exc.folder_id}")
        response = self._create_base_response(request, exc, "recursive_email_error")
        response["folder_id"] = exc.folder_id
        return JSONResponse(status_code=exc.status_code, content=response)

    async def handle_global_error(self, request: Request, exc: Exception):
        stack_trace = traceback.format_exc()
        self.logger.error(
            "Unhandled exception on %s\nError: %s\nStack trace:\n%s",
            request.url, str(exc), stack_trace
        )
        return JSONResponse(
            status_code=500,
            content=self._create_base_response(
                request, 
                Exception("An unexpected error occurred. Please try again later."),
                "internal_server_error"
            )
        )

    async def handle_email_persistence_error(self, request: Request, exc: EmailPersistenceException):
        """Handle email persistence errors with detailed information."""
        error_context = f"Message IDs: {exc.message_ids}"
        if exc.original_error:
            error_context += f", Original error: {str(exc.original_error)}"
        
        self._log_error(request, exc, error_context)
        
        response = self._create_base_response(request, exc, "email_persistence_error")
        if exc.message_ids:
            response["message_ids"] = exc.message_ids
        
        # Add error type information if it's a duplicate error
        if exc.is_duplicate_error():
            response["error_type"] = "duplicate_entry"
        
        return JSONResponse(status_code=exc.status_code, content=response)