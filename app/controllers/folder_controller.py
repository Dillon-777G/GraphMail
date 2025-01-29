import logging
from typing import Union, Dict, Any

import asyncio
from fastapi import APIRouter, Depends
from starlette.responses import RedirectResponse

from app.service.folder_service import FolderService
from app.service.graph_service import Graph
from app.service.email_service import EmailService
from app.fAPI_dependencies.auth_dependency import AuthDependency


logger = logging.getLogger(__name__)

def folder_controller(
    graph: Graph, 
    folder_service: FolderService, 
    email_service: EmailService
) -> APIRouter:
    router = APIRouter()
    auth = AuthDependency(graph)

    @router.get("/root")
    async def list_root_folders(
        auth_response: Union[RedirectResponse, None] = Depends(auth)
    ):
        """
        List all root mail folders in the user's mailbox.
        If the user is not authenticated, returns a RedirectResponse to the
        authentication URL.
        """
        if auth_response:
            # If we got a redirect, immediately return it.
            return auth_response

        # Otherwise, the user is authenticated; proceed with normal logic.
        logger.info("Received request to list root folders")
        folders = await folder_service.get_root_folders()
        return {
            "status": "success",
            "data": [folder.model_dump() for folder in folders]
        }

    @router.get("/{folder_id}/contents")
    async def get_folder_contents(
        folder_id: str,
        auth_response: Union[RedirectResponse, None] = Depends(auth)
    ) -> Dict[str, Any]:
        """
        Get current folder info, its subfolders and messages.
        """
        if auth_response:
            # If we got a redirect, immediately return it.
            return auth_response

        logger.info("Received request to get contents for folder ID: %s", folder_id)

        # User is authenticated, so fetch folder data.
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
