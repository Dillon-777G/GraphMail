import logging
from typing import Union, Dict
import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.service.recursive_email_service import RecursiveEmailService
from app.service.graph.graph_authentication_service import Graph
from app.controllers.fAPI_dependencies.auth_dependency import AuthDependency
from app.models.dto.recursive_email_request_dto import RecursiveEmailRequestDTO

def recursive_email_controller(
    graph: Graph,
    recursive_email_service: RecursiveEmailService
) -> APIRouter:
    router = APIRouter()
    auth = AuthDependency(graph)
    logger = logging.getLogger(__name__)

    @router.post("/folder/{folder_id}/all-emails")
    async def get_all_emails_in_folder(
        folder_id: str,
        request: RecursiveEmailRequestDTO,
        auth_response: Union[Dict[str,str], None] = Depends(auth)
    ) -> EventSourceResponse:
        """
        Recursively retrieve all emails from a folder and its subfolders and persist them to the database.
        If the user is not authenticated, returns a RedirectResponse to the authentication URL.

        Args:
            folder_id: The ID of the folder to start the recursive search from

        Returns:
            EventSourceResponse containing status updates and list of all emails found
        """
        if auth_response:
            return auth_response

        logger.info(
            "Received request to recursively retrieve all emails from folder ID: %s",
            folder_id
        )

        async def event_generator():
            async for item in recursive_email_service.get_all_emails_recursively(folder_id, request):
                if isinstance(item, dict):
                    yield {
                        "event": "progress",
                        "data": json.dumps(item)  # ServiceMetrics handles its own serialization
                    }
                else:
                    # Use Pydantic's built-in serialization for Email models
                    yield {
                        "event": "complete",
                        "data": json.dumps({
                            "status": "success",
                            "data": {
                                "total_emails": len(item),
                                "emails": [email.model_dump(mode='json') for email in item]
                            }
                        })
                    }

        return EventSourceResponse(event_generator())

    return router