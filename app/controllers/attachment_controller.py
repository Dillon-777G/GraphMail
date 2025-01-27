import logging

from fastapi import APIRouter, Request

from app.service.attachment_service import AttachmentService
from app.service.graph_service import Graph
from app.responses.attachment_response import AttachmentDownloadResponse

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

    @router.get("/{folder_name}/{message_id}")
    async def get_attachments(request: Request, folder_name: str, message_id: str):
        """
        Fetch attachments for a specific message in a folder by folder name.

        Args:
            :param message_id: the id of the message.
            :param folder_name: the name of the folder containing the message.
            :param request: the HTTP request.

        Returns:
            JSON: List of attachments for the specified message.
        """
        logger.info("Received request to get attachments for -> \n folder: %s \n message id: %s", folder_name, message_id)
        auth_status = graph.ensure_authenticated(request.query_params.get("code"))
        if not auth_status["authenticated"]:
            return {"status": "Authentication required", "auth_url": auth_status["auth_url"]}

        attachments = await attachment_service.get_message_attachments(folder_name, message_id)
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


    @router.get("/{folder_name}/{message_id}/{attachment_id}/download")
    async def download_attachment(request: Request, folder_name: str, message_id: str, attachment_id: str):
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
        logger.info("Received request to download attachment for -> \n folder: %s, \n message id: %s, \n attachment id: %s", folder_name, message_id, attachment_id)
        
        auth_status = graph.ensure_authenticated(request.query_params.get("code"))
        if not auth_status["authenticated"]:
            return {"status": "Authentication required", "auth_url": auth_status["auth_url"]}

        attachment = await attachment_service.download_attachment(folder_name, message_id, attachment_id)
        
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
