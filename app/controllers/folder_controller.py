import logging
from typing import Union, Dict, Any

from fastapi import APIRouter, Depends, Query

from app.service.folder_service import FolderService
from app.service.graph.graph_authentication_service import Graph
from app.service.emails.paginated_email_service import PaginatedEmailService
from app.controllers.fAPI_dependencies.auth_dependency import AuthDependency


def folder_controller(
    graph: Graph, 
    folder_service: FolderService, 
    paginated_email_service: PaginatedEmailService
) -> APIRouter:
    router = APIRouter()
    auth = AuthDependency(graph)
    logger = logging.getLogger(__name__)

    @router.get("/root")
    async def list_root_folders(
        auth_response: Union[Dict[str,str], None] = Depends(auth)
    ):
        """
        List all root mail folders in the user's mailbox.
        If the user is not authenticated, returns a RedirectResponse to the
        authentication URL.

        NOTE: This is where the user should first be directed to when accessing
        the email bridge.
        """
        if auth_response:
            return auth_response

        logger.info("Received request to list root folders")
        folders = await folder_service.get_root_folders()
        return {
            "status": "success",
            "data": [folder.model_dump() for folder in folders]
        }

    @router.get("/{folder_id}/contents")
    async def get_folder_contents(
        folder_id: str,
        page: int = Query(1, ge=1, description="Page number, starting at 1"),
        per_page: int = Query(25, ge=1, le=100, description="Number of emails per page"),
        auth_response: Union[Dict[str,str], None] = Depends(auth)
    ) -> Dict[str, Any]:
        """
        Get folder info, its subfolders, and paginated messages.
        
        This endpoint allows the client to request a specific page of emails in the folder.
        Page numbering starts at 1.

        NOTE: This endpoint is not allowed to access the parent of Top of Information Store.
        """
        if auth_response:
            # If authentication returns a redirect, immediately return it.
            return auth_response

        logger.info(
            "Received request to get contents for folder ID: %s (page: %d, per_page: %d)",
            folder_id, page, per_page
        )

        # Retrieve folder details
        current_folder = await folder_service.get_folder(folder_id)
        
        # If this is Top of Information Store, remove the parent_folder_id
        if current_folder.display_name == "Top of Information Store":
            current_folder.parent_folder_id = "Not allowed to go here"

        # Continue with existing logic
        folders = await folder_service.get_child_folders(folder_id)

        # Retrieve paginated emails.
        # It is assumed that get_folder_emails_by_id has been modified to accept pagination parameters.
        paginated_emails = await paginated_email_service.get_paginated_emails_by_folder_id(
            folder_id, page=page, per_page=per_page
        )

        # The paginated_emails is assumed to be a dict containing:
        #   - "emails": List of email objects
        #   - "total": Total number of emails in the folder
        #   - "total_pages": Total number of pages available
        emails = paginated_emails.get("emails", [])
        total = paginated_emails.get("total", 0)
        total_pages = paginated_emails.get("total_pages", 1)

        return {
            "status": "success",
            "data": {
                "current_folder": current_folder.model_dump(),
                "subfolders": [folder.model_dump() for folder in folders],
                "emails": [email.model_dump() for email in emails],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages
                }
            }
        }

    return router