import base64
import logging
from typing import List

from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.models.message import Message
from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder
from kiota_abstractions.base_request_configuration import RequestConfiguration
from kiota_abstractions.api_error import APIError


from app.error_handling.exceptions.email_attachment_exception import EmailAttachmentException
from app.error_handling.exceptions.graph_response_exception import GraphResponseException
from app.error_handling.exceptions.email_exception import EmailException

from app.models.email_attachment import EmailAttachment
from app.service.retry_service import RetryService
from app.models.retries.retry_context import RetryContext
from app.models.retries.retry_enums import RetryProfile
from app.models.metrics.attachment_metrics import AttachmentMetrics

from app.service.graph.graph_authentication_service import Graph
from app.service.emails.email_crud_service import EmailCRUDService
from app.service.attachments.attachment_crud_service import AttachmentCRUDService
from app.utils.attachment_utils import AttachmentUtils
from app.service.attachments.attachment_file_service import AttachmentFileService

"""
SUMMARY:


This class is responsible for getting the attachment responses from graph API


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
class AttachmentGraphService:
    def __init__(self, graph: Graph, email_crud_service: EmailCRUDService, 
                 attachment_crud_service: AttachmentCRUDService,
                 attachment_file_service: AttachmentFileService):
        self.graph = graph
        self.logger = logging.getLogger(__name__)
        self.retry_service = RetryService(retry_profile=RetryProfile.FAST)
        self.email_crud_service = email_crud_service 
        self.attachment_crud_service = attachment_crud_service
        self.attachment_file_service = attachment_file_service



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

        Raises:
            EmailAttachmentException: If the attachment is not found or is an
            unsupported type.
        """
        metrics = self.__start_metrics(folder_id, message_id, attachment_id)
        
        try:
            self.logger.info("Starting download service for attachment: %s", attachment_id)
            # Start processing time is tracked by metrics.start_processing()
            metrics.current_phase = "fetching attachment"
            raw_attachment = await self.__get_attachment(folder_id, message_id, attachment_id)
            email_id = await self.email_crud_service.get_email_id_by_graph_message_id(message_id)
            metrics.current_phase = "processing attachment"
            processed_data = await self.__process_attachment(raw_attachment, email_id)
            metrics.current_phase = "complete"
            
            # Record metrics after successful processing
            metrics.record_download(raw_attachment.size)
            return processed_data
            
        except APIError as e:
            # Record API-specific failures with detailed error info
            error_message = f"API Error: {str(e.message if e.message else str(e))}"
            metrics.record_download_failure(error_message)
            self.logger.error("API Error on downloading attachment: %s", error_message)
            raise EmailAttachmentException(
                detail=f"Attachment {attachment_id} not found or cannot be accessed.",
                attachment_id=attachment_id,
                status_code=404
            ) from e
        except Exception as e:
            # Record all other failures
            metrics.record_download_failure(str(e))
            raise
        finally:
            metrics.end_processing()  # End timing for the entire operation
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
            APIError: If there's an API-specific error (allowing parent to handle)
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
            error_msg=f"Failed to retrieve attachment {attachment_id}"
        )

        try:
            return await self.retry_service.retry_operation(retry_context)
        except APIError:
            # Let APIError propagate to parent for handling
            raise
        except Exception as e:
            raise EmailAttachmentException(
                detail=f"Error retrieving attachment: {str(e)}",
                attachment_id=attachment_id,
                status_code=500
            ) from e




    async def __process_attachment(self, raw_attachment: FileAttachment, email_id: int) -> dict:
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

        # Create and save DB record
        db_attachment = AttachmentUtils.attachment_to_db_attachment(attachment, email_id)
        print(f"DB Attachment url: {db_attachment.url}")
        await self.attachment_crud_service.save_attachment(db_attachment)

        content_bytes = attachment.content_bytes
        data = {
            column.name: getattr(db_attachment, column.name)
            for column in db_attachment.__table__.columns
        }
        if content_bytes:
            try:
                decoded_content = base64.b64decode(content_bytes)
                self.logger.debug("Content type: %s", raw_attachment.content_type)
                await self.attachment_file_service.save_attachment_file(db_attachment, decoded_content)

            except Exception as e:
                raise EmailAttachmentException(
                    detail=f"Failed to process attachment content for {attachment.id}: {str(e)}",
                    attachment_id=attachment.id,
                    status_code=500
                ) from e
        self.logger.info("Finished processing attachment, attachment data: %s", data)
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
        self.logger.info("Starting fetch message attachments service for message: %s", message_id)
        metrics = self.__start_metrics(folder_id, message_id, None)

        async def fetch():
            metrics.current_phase = "fetching attachments"
            message = await self.graph.client.me.mail_folders.by_mail_folder_id(
                    folder_id
                ).messages.by_message_id(message_id).get(
                    request_configuration=RequestConfiguration(
                        query_parameters=MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
                            expand=["attachments"]
                        )
                    )
                )

            self.__validate_message_and_attachments(message, folder_id, message_id)
            metrics.attachments_processed = len(message.attachments)
                
            # Filter for file attachments only and convert them
            attachments = [
                EmailAttachment.graph_email_attachment(att)
                for att in message.attachments
                if att.odata_type == "#microsoft.graph.fileAttachment"
            ]
            
            return attachments

        retry_context = RetryContext(
            operation=fetch,
            error_msg=f"Failed to retrieve attachments for message {message_id}"
        )

        try:
            result = await self.retry_service.retry_operation(retry_context)
            metrics.current_phase = "complete"
            return result
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
            metrics.log_metrics_fetch(self.logger)




    
    def __validate_message_and_attachments(self, message: Message, folder_id: str, message_id: str):
        if not message:
            self.logger.error("No message found for message ID %s", message_id)
            raise EmailException(
                detail=f"No message found for message ID {message_id}",
                folder_id=folder_id,
                message_id=message_id,
                status_code=404
            )
        
        if not message.attachments:
            self.logger.info("No attachments found for message ID %s", message_id)
            raise EmailAttachmentException(
                detail=f"No attachments found for message ID {message_id}",
                attachment_id=message_id,
                status_code=404
            )





    def __start_metrics(self, folder_id: str, message_id: str, attachment_id: str):
        metrics = AttachmentMetrics()
        metrics.start_processing()
        metrics.folder_id = folder_id
        metrics.message_id = message_id
        metrics.attachment_id = attachment_id
        metrics.current_phase = "initializing"
        return metrics
# End of file
