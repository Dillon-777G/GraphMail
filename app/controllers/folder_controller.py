import logging
import asyncio

from fastapi import APIRouter, Request

from app.service.folder_service import FolderService
from app.service.graph_service import Graph
from app.service.email_service import EmailService

logger = logging.getLogger(__name__)

def folder_controller(graph: Graph, folder_service: FolderService, email_service: EmailService) -> APIRouter:
    """
    Defines routes for managing mail folders and their contents.

    Args:
        graph (Graph): The Graph service instance.
        folder_service (FolderService): Service for handling folder operations.
        email_service (EmailService): Service for handling email operations.

    Returns:
        APIRouter: The router object for folder endpoints.
    """
    router = APIRouter()

    @router.get("/root")
    async def list_root_folders(request: Request):
        """
        List all root mail folders in the user's mailbox.
        Handles authentication if necessary.
        """
        logger.info("Received request to list root folders")
        
        auth_status = graph.ensure_authenticated(request.query_params.get("code"))
        if not auth_status["authenticated"]:
            return {"status": "Authentication required", "auth_url": auth_status["auth_url"]}

        folders = await folder_service.get_root_folders()
        return {
            "status": "success",
            "data": [folder.model_dump() for folder in folders]
        }

    @router.get("/{folder_id}/contents")
    async def get_folder_contents(request: Request, folder_id: str):
        """
        Get current folder info, its subfolders and messages.
        Handles authentication if necessary.
        """
        logger.info("Received request to get contents for folder ID: %s", folder_id)
        
        auth_status = graph.ensure_authenticated(request.query_params.get("code"))
        if not auth_status["authenticated"]:
            return {"status": "Authentication required", "auth_url": auth_status["auth_url"]}

        # Get current folder, subfolders and messages in parallel
        current_folder = await folder_service.get_folder(folder_id)
        folders, messages = await asyncio.gather(
            folder_service.get_child_folders(folder_id),
            email_service.get_folder_emails_by_id(folder_id)
        )

        return {
            "status": "success",
            "data": {
                "current_folder": current_folder.model_dump(),
                "subfolders": [folder.model_dump() for folder in folders],
                "messages": [message.model_dump() for message in messages]
            }
        }

    return router
