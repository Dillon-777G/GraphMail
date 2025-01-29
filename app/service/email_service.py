import logging
from typing import List

from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.models.message_collection_response import MessageCollectionResponse

from app.utils.graph_utils import GraphUtils
from app.models.email import Email
from app.exception.exceptions import EmailException, IdTranslationException

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, graph_utils: GraphUtils):
        self.graph_utils = graph_utils

    async def get_folder_emails_by_id(self, folder_id: str) -> List[Email]:
        """
        Retrieves emails from a specified folder by its ID.

        Args:
            folder_id (str): The ID of the folder.

        Returns:
            List[Email]: A list of emails in the specified folder.

        Raises:
            FolderException: If the folder cannot be accessed
            IdTranslationException: If email IDs cannot be translated
        """
        try:
            # Configure request to include attachments
            query_params = {"expand": ["attachments"]}
            request_configuration = RequestConfiguration(query_parameters=query_params)


            # Get messages from folder with attachments
            messages = await self.graph_utils.graph.client.me.mail_folders.by_mail_folder_id(
                folder_id
            ).messages.get(request_configuration=request_configuration)

            # If there are no messages, return an empty list
            if not messages or not self.graph_utils.get_collection_value(
                messages, MessageCollectionResponse
            ):
                logger.info(
                    "No messages found in folder ID %s. Response: %s", folder_id, messages
                )
                return []

            # Translate message IDs to immutable IDs
            rest_ids = [
                msg.id
                for msg in self.graph_utils.get_collection_value(
                    messages, MessageCollectionResponse
                )
                if msg.id
            ]
            translated_ids = await self.graph_utils.translate_ids(rest_ids)
            id_mapping = {item["source_id"]: item["target_id"] for item in translated_ids}

            # Create Email objects with immutable IDs
            emails = [
                Email.from_graph_message(msg, id_mapping[msg.id])
                for msg in self.graph_utils.get_collection_value(
                    messages, MessageCollectionResponse
                )
                if msg.id in id_mapping
            ]

            return emails

        except IdTranslationException as e:
            logger.error("ID translation error: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error retrieving emails from folder ID '%s': %s", folder_id, str(e))
            raise EmailException(
                detail=f"Failed to retrieve emails from folder: {str(e)}",
                status_code=500,
            ) from e

    async def get_folder_emails(self, folder_name: str) -> List[Email]:
        """
        Retrieves emails from a specified folder by its name.

        Args:
            folder_name (str): The name of the folder.

        Returns:
            List[Email]: A list of emails in the specified folder.

        Raises:
            FolderException: If the folder cannot be found or accessed
            IdTranslationException: If email IDs cannot be translated
        """
        # Get folder ID
        folder_id = await self.graph_utils.get_folder_id_by_name(folder_name)
        
        try:
            # Configure request to include attachments
            request_configuration = RequestConfiguration(query_parameters={
                "$expand": "attachments($select=id,@odata.type)"
            })
            
            # Get messages from folder with attachments
            messages = await self.graph_utils.graph.client.me.mail_folders.by_mail_folder_id(folder_id).messages.get(
                request_configuration=request_configuration
            )
            # Translate message IDs to immutable IDs
            rest_ids = [msg.id for msg in self.graph_utils.get_collection_value(messages, MessageCollectionResponse) if msg.id]
            translated_ids = await self.graph_utils.translate_ids(rest_ids)
            id_mapping = {item['source_id']: item['target_id'] for item in translated_ids}

            # Create Email objects with immutable IDs and check attachments
            emails = [
                Email.from_graph_message(msg, id_mapping[msg.id])
                for msg in self.graph_utils.get_collection_value(messages, MessageCollectionResponse)
                if msg.id in id_mapping
            ]
            
            # Update has_attachments based on both regular and inline attachments
            # for email in emails:
            #     email.has_attachments = email.effective_has_attachments

            return emails

        except IdTranslationException:
            raise
        except Exception as e:
            logger.error("Error retrieving emails from folder %s: %s", folder_name, str(e))
            raise EmailException(
                detail=f"Failed to retrieve emails from folder: {str(e)}",
                folder_name=folder_name,
                status_code=500
            ) from e