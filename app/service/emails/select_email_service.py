from typing import List, Dict
import logging

from app.service.graph.graph_authentication_service import Graph
from app.service.graph.graph_id_translation_service import GraphIDTranslator
from app.service.emails.paginated_email_service import PaginatedEmailService

from app.models.email import Email
from app.models.persistence_models.email_orm import DBEmail
from app.models.retries.retry_enums import RetryProfile
from app.models.dto.email_selection_dto import EmailSelectionDTO

from app.error_handling.exceptions.email_exception import EmailException
from app.error_handling.exceptions.id_translation_exception import IdTranslationException
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException

from app.service.retry_service import RetryService
from app.models.retries.retry_context import RetryContext

from app.repository.email_repository import EmailRepository
from app.repository.email_recipient_repository import EmailRecipientRepository
from app.utils.email_utils import EmailUtils




"""
SUMMARY:

This class is responsible for allowing users to pass up to 50 email IDs to selectively download.
It leverages a cache of folders that the user has recently visited in order to ensure quick lookups.
If the cache fails, it will default to an api call to fetch the emails. 

"""
class SelectEmailService:
    def __init__(
        self, 
        graph: Graph,
        graph_translator: GraphIDTranslator,
        email_repository: EmailRepository,
        email_recipient_repository: EmailRecipientRepository,
        paginated_email_service: PaginatedEmailService
    ):
        self.graph = graph
        self.graph_translator = graph_translator
        self.email_repository = email_repository
        self.email_recipient_repository = email_recipient_repository
        self.paginated_email_service = paginated_email_service
        self.logger = logging.getLogger(__name__)
        self.retry_service = RetryService(retry_profile=RetryProfile.STANDARD)
        self.max_messages = 50




    async def select_and_persist_emails(
        self, 
        folder_id: str,
        selection: EmailSelectionDTO
    ) -> List[DBEmail]:
        """
        Fetch specific emails using cache when possible and persist them to the database.
        
        Args:
            selection (EmailSelectionDTO): Selection parameters including source IDs and reference info
            
        Returns:
            List[DBEmail]: List of persisted DBEmail objects
            
        Raises:
            EmailException: If there's an error fetching or processing the emails
            IdTranslationException: If ID translation fails
            EmailPersistenceException: If persistence fails
        """
        try:
            # Validate selection
            self._validate_source_ids(selection.email_source_ids)

            # Try to get emails from cache first
            emails = await self.paginated_email_service.get_cached_emails_by_ids(
                folder_id, 
                selection.email_source_ids
            )
            
            self._validate_emails(emails, folder_id)
            id_mapping_dict = await self._translate_ids_parallel(selection)
            self._validate_id_mappings(id_mapping_dict, emails)
            
            # First convert and save emails
            db_emails = []
            for email in emails:
                immutable_id = id_mapping_dict[email.source_id]
                db_email = EmailUtils.email_to_db_email(
                    email=email,
                    selection=selection,
                    immutable_id=immutable_id
                )
                db_emails.append(db_email)


            successful_emails, duplicate_emails, failed_emails = await self.email_repository.bulk_save_emails(db_emails)

            # Extract and save recipients for successful emails
            all_recipients = []
            if successful_emails:
                all_recipients = EmailUtils.extract_recipients_from_init_response_emails(emails, successful_emails)
                # Save recipients - any failure here will raise an exception
                if all_recipients:
                    await self.email_recipient_repository.bulk_save_recipients(all_recipients)
            else:
                self.logger.error("No recipients to save, there are no successful emails")
                 

            
            successful_email_ids, duplicate_email_ids, failed_email_ids = EmailUtils.extract_email_ids_from_results(
                successful_emails, duplicate_emails, failed_emails
            )

            return successful_email_ids, duplicate_email_ids, failed_email_ids

        except EmailPersistenceException as e:
            if e.is_duplicate_error():
                self.logger.warning("Attempted to persist duplicate emails: %s", e.message_ids)
            else:
                self.logger.error("Error in select and persist operation: %s", str(e))
            raise
        except Exception as e:
            self.logger.error("Error in select and persist operation: %s", str(e))
            raise EmailException(
                detail=f"Failed to select and persist emails: {str(e)}",
                status_code=500
            ) from e






    async def _batch_translate_ids(self, source_ids: List[str], batch_size: int = 20) -> List[Dict[str, str]]:
        """
        Translate source IDs to immutable IDs in batches.
        
        Args:
            source_ids: List of source IDs to translate
            batch_size: Size of each batch for translation
            
        Returns:
            List[Dict[str, str]]: List of mappings from source to translated IDs
        """
        all_translated_ids = []
        for i in range(0, len(source_ids), batch_size):
            batch = source_ids[i:i + batch_size]
            try:
                translated_batch = await self.graph_translator.translate_ids(batch)
                all_translated_ids.extend(translated_batch)
            except Exception as e:
                self.logger.error("Error translating batch of IDs: %s", str(e))
                raise IdTranslationException(
                    detail=f"Failed to translate batch of IDs: {str(e)}",
                    source_ids=batch,
                    status_code=500
                ) from e

        return all_translated_ids



    ##############
    # VALIDATORS #
    ##############

    def _validate_source_ids(self, source_ids: List[str]) -> None:
        """Validate the source IDs."""
        if len(source_ids) > self.max_messages:
            raise EmailException(
                detail=f"Too many message IDs provided. Maximum allowed is {self.max_messages}",
                status_code=400
            )

    def _validate_emails(self, emails: List[Email], folder_id: str):
        if not emails:
            raise EmailException(
                detail="Could not retrieve emails from cache or API",
                folder_id=folder_id,
                status_code=404
            )

    def _validate_id_mappings(self, id_mapping_dict: Dict[str,str], emails: List[Email]):
        missing_translations = [
                email.source_id for email in emails 
                if email.source_id not in id_mapping_dict
            ]
        if missing_translations:
            raise IdTranslationException(
                 detail="Failed to obtain immutable IDs for some messages",
                source_ids=missing_translations,
                status_code=500
            )




    async def _translate_ids_parallel(self, selection_dto: EmailSelectionDTO) -> Dict[str,str]:
        translate_context = RetryContext(
                operation=lambda: self._batch_translate_ids(selection_dto.email_source_ids),
                error_msg="Failed to translate IDs",
                custom_exception=IdTranslationException
            )
        translated_ids = await self.retry_service.retry_operation(translate_context)
        id_mapping = {item["source_id"]: item["target_id"] for item in translated_ids}
        return id_mapping