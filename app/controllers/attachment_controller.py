import logging
from typing import Union, Dict

from fastapi import APIRouter, Depends

from app.service.attachment_service import AttachmentService
from app.service.graph.graph_authentication_service import Graph
from app.responses.attachment_response import AttachmentDownloadResponse
from app.controllers.fAPI_dependencies.auth_dependency import AuthDependency

logger = logging.getLogger(__name__)


def attachment_controller(graph: Graph, attachment_service: AttachmentService) -> APIRouter:
    """
    Defines routes for managing email attachments.

    Args:
        graph (Graph): The Graph service instance.
        attachment_service (AttachmentService): Service for handling attachment operations.

    Returns:
        APIRouter: The router object for attachment endpoints.
    """
    router = APIRouter()
    auth = AuthDependency(graph)


    @router.get("/{folder_id}/{message_id}")
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
        
        attachments = await attachment_service.get_message_attachments(folder_id, message_id)
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


    @router.get("/{folder_id}/{message_id}/{attachment_id}/download")
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
        
        attachment = await attachment_service.download_attachment(folder_id, message_id, attachment_id)
        
        # Create metadata dictionary
        metadata = {
            "id": attachment["id"],
            "name": attachment["name"],
            "content_type": attachment["content_type"],
            "size": attachment["size"]
        }

        return AttachmentDownloadResponse(
            file_content=attachment["content_bytes"],
            content_type=attachment["content_type"],
            filename=attachment["name"],
            metadata=metadata
        )


    return router
