import base64
import logging
from typing import List

from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration


from app.error_handling.exceptions.email_attachment_exception import EmailAttachmentException
from app.error_handling.exceptions.graph_response_exception import GraphResponseException
from app.models.email_attachment import EmailAttachment
from app.utils.retry_utils import RetryUtils
from app.models.retries.retry_context import RetryContext
from app.models.retries.retry_enums import RetryProfile
from app.models.metrics.attachment_metrics import AttachmentMetrics
from app.service.graph.graph_authentication_service import Graph

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
    def __init__(self, graph: Graph):
        self.graph = graph
        self.logger = logging.getLogger(__name__)
        self.retry_utils = RetryUtils(retry_profile=RetryProfile.FAST)

    async def download_attachment(self, folder_id: str,
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
        metrics = self.__start_metrics(folder_id, message_id)
        
        try:
            # Start processing time is tracked by metrics.start_processing()
            raw_attachment = await self.__get_attachment(folder_id, message_id, attachment_id)
            processed_data = self.__process_attachment(raw_attachment)
            
            # Record metrics after successful processing
            metrics.record_download(
                len(processed_data.get("content_bytes", b""))
            )
            return processed_data
            
        except Exception as e:
            metrics.record_download_failure(attachment_id, str(e))
            raise
        finally:
            metrics.end_processing()  # End timing for the entire operation
            metrics.current_phase = "complete"
            metrics.log_metrics_download(self.logger)



    async def __get_attachment(self, folder_id: str,
                                message_id: str, attachment_id: str) -> FileAttachment:
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
        async def fetch():
            return await (
                self.graph.client.me.mail_folders
                .by_mail_folder_id(folder_id)
                .messages.by_message_id(message_id)
                .attachments.by_attachment_id(attachment_id)
                .get()
            )

        retry_context = RetryContext(
            operation=fetch,
            error_msg=f"Failed to retrieve attachment {attachment_id}",
            custom_exception=lambda detail, status_code: EmailAttachmentException(
                detail=detail,
                attachment_id=attachment_id,
                status_code=status_code
            )
        )

        try:
            return await self.retry_utils.retry_operation(retry_context)
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

        

    async def get_message_attachments(self, folder_id: str,
                                        message_id: str) -> List[EmailAttachment]:
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
        end. I don't think it will be fixed. The current workaround I am using is to 
        query it the same as I do in the email service but then only return the filtered
        attachments.

        LINKS:
        https://learn.microsoft.com/en-us/answers/questions/360481/filtering-attachments-in-graph-api-does-not-work
        https://stackoverflow.com/questions/72391953/microsoft-graph-api-for-email-attachment-cant-filter-by-size
        """
        metrics = self.__start_metrics(folder_id, message_id)
        
        async def fetch():
            message = await self.graph.client.me.mail_folders.by_mail_folder_id(
                    folder_id
                ).messages.by_message_id(message_id).get(
                    request_configuration=RequestConfiguration(
                        query_parameters=MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
                            expand=["attachments"]
                        )
                    )
                )

            if not message or not message.attachments:
                self.logger.info("No attachments found for message ID %s", message_id)
                return []

            # Filter for file attachments only and convert them
            attachments = [
                EmailAttachment.graph_email_attachment(att)
                for att in message.attachments
                if att.odata_type == "#microsoft.graph.fileAttachment"
            ]
            
            metrics.record_fetch(len(attachments))
            return attachments

        retry_context = RetryContext(
            operation=fetch,
            error_msg=f"Failed to retrieve attachments for message {message_id}",
            custom_exception=EmailAttachmentException
        )

        try:
            return await self.retry_utils.retry_operation(retry_context)
        except GraphResponseException as e:
            self.logger.error("Failed to retrieve attachments for message %s: %s", message_id, str(e))
            raise
        except Exception as e: 
            raise EmailAttachmentException(
                detail=f"Failed to retrieve attachments for message {message_id}",
                status_code=500 # pylint: disable=R0801 # Streamline exception handling, R0801 warning on folder_service[64:69]
            ) from e
        finally:
            metrics.end_processing()  # End timing for the entire operation
            metrics.current_phase = "complete"
            metrics.log_metrics_fetch(self.logger)



    def __start_metrics(self, folder_id: str, message_id: str):
        metrics = AttachmentMetrics()
        metrics.start_processing()
        metrics.folder_id = folder_id
        metrics.message_id = message_id
        return metrics
# End of file
