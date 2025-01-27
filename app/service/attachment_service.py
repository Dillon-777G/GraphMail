import base64
import logging
from typing import List

from msgraph.generated.models.attachment_collection_response import AttachmentCollectionResponse
from msgraph.generated.models.file_attachment import FileAttachment

from app.exception.exceptions import EmailAttachmentException, GraphResponseException
from app.utils.graph_utils import GraphUtils
from app.models.email_attachment import EmailAttachment

logger = logging.getLogger(__name__)

"""
NOTE: Attachment objects in Microsoft Graph already support
 immutable IDs, as inferred from observed API behavior.

Attempts to translate attachment IDs (e.g., to immutable ids) resulted in errors:
    APIError: 400 Bad Request
    Message: 'Invalid value for arg: storeObjectId.IdType,
     value: ImmutableId, expected: EntryId'

This suggests the provided attachment IDs are already immutable.
As a result, ID translation has been omitted. 
For more details on fileAttachment objects, refer to the
 email_attachment class or the Microsoft Graph documentation.
"""
class AttachmentService:
    def __init__(self, graph_utils: GraphUtils):
        self.graph_utils = graph_utils

    async def download_attachment(self, folder_name: str,
     message_id: str, attachment_id: str) -> dict:
        """
        Download a specific file attachment from a message.

        Args:
            folder_name (str): The name of the folder containing the message.
            message_id (str): The ID of the message.
            attachment_id (str): The ID of the attachment.

        Returns:
            dict: Contains attachment metadata and content for file download.
            NOTE: the metadata is stored in the response headers.

        Raises:
            EmailAttachmentException: If the attachment is not found or is an
            unsupported type.
        """
        folder_id = await self.graph_utils.get_folder_id_by_name(folder_name)
        raw_attachment = await self.__get_attachment(folder_id, message_id, attachment_id)
        return self.__process_attachment(raw_attachment)

    async def __get_attachment(self, folder_id: str, message_id: str, attachment_id: str) -> FileAttachment:
        """
        Calls the get attachment function and handles exceptions properly.

        Args:
            folder_id: The ID of the folder containing the message
            message_id: The ID of the message
            attachment_id: The ID of the attachment

        Returns:
            The attachment content

        Raises:
            EmailAttachmentException: If the attachment is not found or cannot be retrieved
        """
        try:
            return await (
                self.graph_utils.graph.client.me.mail_folders
                .by_mail_folder_id(folder_id)
                .messages.by_message_id(message_id)
                .attachments.by_attachment_id(attachment_id)
                .get()
            )
        except Exception as e:
            raise EmailAttachmentException(
                detail=f"Attachment {attachment_id} not found or cannot be accessed.",
                attachment_id=attachment_id,
                status_code=404
            ) from e

    # noinspection PyMethodMayBeStatic
    def __process_attachment(self, raw_attachment: FileAttachment) -> dict:
        """
        Process a raw attachment and validate it.

        Args:
            raw_attachment: The raw attachment data from Microsoft Graph.

        Returns:
            dict: Processed attachment metadata and content.

        Raises:
            EmailAttachmentException: If the attachment is invalid or content cannot be decoded.
        """
        attachment = EmailAttachment.graph_email_attachment(raw_attachment)
        attachment.is_valid_file_attachment()

        data = attachment.model_dump()
        if data["content_bytes"]:
            try:
                data["content_bytes"] = base64.b64decode(data["content_bytes"])
            except Exception as e:
                raise EmailAttachmentException(
                    detail=f"Failed to decode attachment content for {attachment.id}: {str(e)}",
                    attachment_id=attachment.id,
                    status_code=500
                ) from e
        return data

    async def get_message_attachments(self, folder_name: str, message_id: str) -> List[EmailAttachment]:
        """
        Fetch all file attachments for a specific message in a folder.

        Args:
            folder_name (str): The name of the folder containing the message.
            message_id (str): The ID of the message.

        Returns:
            List[Attachment]: A list of file attachments for the specified message.

        NOTE: This code has been adjusted to strictly not support item attachments. 
        They are rare and we do not need the extra processing logic because they will
        not contain data relevant to our use case.

        NOTE: Attachment endpoints from the graph API do not support the filter
        parameter. This has been a known issue for roughly 4 years on Microsoft's 
        end. I don't think it will be fixed. The current workaround I am going to 
        use is to query it like a message and then use expand to filter.

        LINKS:
        https://learn.microsoft.com/en-us/answers/questions/360481/filtering-attachments-in-graph-api-does-not-work
        https://stackoverflow.com/questions/72391953/microsoft-graph-api-for-email-attachment-cant-filter-by-size
        """
        try:
            folder_id = await self.graph_utils.get_folder_id_by_name(folder_name)

            # Get the attachments
            response: AttachmentCollectionResponse = await (
                self.graph_utils.graph.client.me.mail_folders
                .by_mail_folder_id(folder_id)
                .messages.by_message_id(message_id)
                .attachments.get()
            )

            return [
                EmailAttachment.graph_email_attachment(att)
                for att in self.graph_utils.get_collection_value(response, AttachmentCollectionResponse)
            ]

        except GraphResponseException as e:
            logger.error("Failed to retrieve attachments for message %s: %s", message_id, str(e))
            raise e
        except Exception as e:
            raise EmailAttachmentException(
                detail=f"Failed to retrieve attachments for message {message_id}",
                status_code=500
            ) from e

# End of file
