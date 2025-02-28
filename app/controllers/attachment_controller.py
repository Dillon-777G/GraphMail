# Python standard library imports
import logging
from typing import Dict, Union

# Third party imports
from fastapi import APIRouter, Depends

# Application imports
from app.controllers.fAPI_dependencies.auth_dependency import AuthDependency
from app.service.attachments.attachment_graph_service import AttachmentGraphService
from app.service.graph.graph_authentication_service import Graph

logger = logging.getLogger(__name__)


def attachment_controller(graph: Graph, attachment_graph_service: AttachmentGraphService) -> APIRouter:
    """
    Defines routes for managing email attachments.

    Args:
        graph (Graph): The Graph service instance.
        attachment_graph_service (AttachmentGraphService): Service for handling attachment operations.

    Returns:
        APIRouter: The router object for attachment endpoints.
    """
    router = APIRouter()
    auth = AuthDependency(graph)


    @router.get("/{folder_id}/{message_id}") # modify for message searh only 
    async def get_attachments(folder_id: str, message_id: str,
     auth_response: Union[Dict[str,str], None] = Depends(auth)):
        """
        Fetch attachments for a specific message in a folder by folder name.

        Args:
            :param message_id: the id of the message.
            :param folder_name: the name of the folder containing the message.
            :param request: the HTTP request.

        Returns:
            JSON: List of attachments for the specified message.
        """
        logger.info("Received request to get attachments for -> \n folder id: %s \n message id: %s", folder_id, message_id)
        
        if auth_response:
            return auth_response
        
        attachments = await attachment_graph_service.get_message_attachments(folder_id, message_id)
        return {
                "status": "success",
                "data": [
                    {
                        "id": attachment.id,
                        "name": attachment.name,
                        "content_type": attachment.content_type,
                        "size": attachment.size
                    }
                    for attachment in attachments
                ]
            }


    @router.post("/{folder_id}/{message_id}/{attachment_id}/download") # modify for message search only 
    async def download_attachment(folder_id: str, message_id: str, attachment_id: str,
     auth_response: Union[Dict[str,str], None] = Depends(auth)):
        """
        Download a specific file attachment from a message.

        Args:
            folder_name: The name of the folder containing the message
            message_id: The ID of the message
            attachment_id: The ID of the attachment
            request: The HTTP request

        Returns:
            AttachmentResponse: The file content and metadata as a downloadable attachment

        NOTE: This function will only work with fileAttachments
        """
        logger.info("Received request to download attachment for -> \n folder id: %s, \n message id: %s, \n attachment id: %s", folder_id, message_id, attachment_id)
        
        if auth_response:
            return auth_response
        
        db_attachment = await attachment_graph_service.download_attachment(folder_id, message_id, attachment_id)
        
        return {
            "status": "success",
            "data": db_attachment # modify to only return the primary key of the attachment
        }


    return router
