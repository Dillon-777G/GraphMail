# Python standard library imports
import json
import logging
from typing import Any, Dict, Union

# Third party imports
from fastapi import APIRouter, Depends, Request
from kiota_abstractions.api_error import APIError
from sse_starlette.sse import EventSourceResponse

# Application imports
from app.controllers.fAPI_dependencies.auth_dependency import AuthDependency
from app.error_handling.exception_config import get_exception_handlers
from app.error_handling.exception_handler_manager import ExceptionHandlerManager
from app.models.dto.recursive_email_request_dto import RecursiveEmailRequestDTO
from app.service.emails.recursive_email_service import RecursiveEmailService
from app.service.graph.graph_authentication_service import Graph


"""
SUMMARY:

This file contains the high level controller for the recursive email service.
It has a dependency on the recursive email service and the exception handler manager.
The exception handler manager is needed because the SSE event stream needs to be able to handle exceptions.
With this handler, the controller can now return detailed error messages to the client, instead of connection closed.
"""
def recursive_email_controller(
    graph: Graph,
    recursive_email_service: RecursiveEmailService,
    exception_handler_manager: ExceptionHandlerManager
) -> APIRouter:
    router = APIRouter()
    auth = AuthDependency(graph)
    logger = logging.getLogger(__name__)




    @router.post("/folder/{folder_id}/all_emails")
    async def get_all_emails_in_folder(
        request: Request,
        folder_id: str,
        email_request: RecursiveEmailRequestDTO,
        auth_response: Union[Dict[str,str], None] = Depends(auth)
    ) -> EventSourceResponse:
        """
        Recursively retrieve all emails from a folder and its subfolders and persist them to the database.
        If the user is not authenticated, returns a RedirectResponse to the authentication URL.

        Args:
            folder_id: The ID of the folder to start the recursive search from

        Returns:
            EventSourceResponse containing status updates and list of all emails found

            NOTE:
            - The successful ids are the email ids in the database
            - the duplicate ids are the graph message ids
            - the failure ids are the graph source ids
        """
        if auth_response:
            return auth_response

        logger.info(
            "Received request to recursively retrieve all emails from folder ID: %s",
            folder_id
        )

        async def event_generator():
            try:
                async for status_update in recursive_email_service.get_all_emails_recursively(folder_id, email_request):
                    yield {"data": json.dumps(status_update)}
            except Exception as e: # pylint: disable=broad-exception-caught
                error_response = await _handle_exception(request, e)
                yield {"data": json.dumps(error_response)}

        return EventSourceResponse(event_generator())







    async def _handle_exception(request: Request, exc: Exception) -> Dict[str, Any]:
        """
        Helper method to handle exceptions and format them for SSE responses.
        
        Args:
            request: The FastAPI request object
            exc: The exception to handle
            
        Returns:
            A dictionary formatted for SSE with error details
        """
        if isinstance(exc, APIError):
            # Handle API errors
            handler_response = await exception_handler_manager.handle_api_error(request, exc)
            error_content = handler_response.body.decode('utf-8')
            error_json = json.loads(error_content)
            
            return {
                "status": "error",
                "message": error_json.get("detail", "Graph API error"),
                "status_code": error_json.get("status_code"),
                "error_code": error_json.get("error_code"),
            }
        
        # Handle other exceptions by checking their type
        handler_response = None
        
        # Check for specific exception types based on their class
        for exception_type, handler_method in get_exception_handlers(exception_handler_manager).items():
            if isinstance(exception_type, type) and isinstance(exc, exception_type):
                handler_response = await handler_method(request, exc)
                break
        
        # Fall back to global error handler if no specific handler was found
        if not handler_response:
            handler_response = await exception_handler_manager.handle_global_error(request, exc)
            
        if handler_response:
            error_content = handler_response.body.decode('utf-8')
            error_json = json.loads(error_content)
                
            return {
                "status": "error",
                "message": error_json.get("detail", "An error occurred"),
                "type": error_json.get("type", "server_error")
            }
        
        # Last resort fallback
        return {
            "status": "error",
            "message": f"Failed to retrieve emails: {str(exc)}",
            "type": "server_error"
        }

    return router