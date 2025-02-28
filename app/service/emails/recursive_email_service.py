# Python standard library imports
import logging
from typing import Any, AsyncGenerator, Dict, List, Union

# Third party imports
from kiota_abstractions.api_error import APIError

# Application imports
from app.error_handling.exceptions.email_exception import EmailException
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException
from app.error_handling.exceptions.folder_exception import FolderException
from app.error_handling.exceptions.recursive_email_exception import RecursiveEmailException
from app.models.dto.recursive_email_request_dto import RecursiveEmailRequestDTO
from app.models.email import Email
from app.repository.email_recipient_repository import EmailRecipientRepository
from app.repository.email_repository import EmailRepository
from app.service.emails.email_cache_service import EmailCacheService
from app.service.emails.email_collection_service import EmailCollectionService
from app.service.folder_service import FolderService
from app.utils.email_utils import EmailUtils

class RecursiveEmailService:
    def __init__(
        self, 
        folder_service: FolderService, 
        email_collection_service: EmailCollectionService,
        email_cache_service: EmailCacheService,
        email_repository: EmailRepository,
        email_recipient_repository: EmailRecipientRepository
    ):
        self.folder_service = folder_service
        self.email_collection_service = email_collection_service
        self.logger = logging.getLogger(__name__)
        self.email_cache_service = email_cache_service
        self.email_repository = email_repository
        self.email_recipient_repository = email_recipient_repository

        

    async def get_all_emails_recursively(
        self, 
        folder_id: str,
        request: RecursiveEmailRequestDTO
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Recursively retrieve and persist all emails from a folder and its subfolders.
        Yields status updates about the operation progress and finally returns
        the IDs of successful, duplicate, and failed emails.
        """
        try:
            all_emails = []
            yield {"status": "initializing", "message": "Starting recursive email retrieval", "folder_id": folder_id}
            async for item in self._get_all_emails_recursively_internal(folder_id):
                if isinstance(item, list):
                    all_emails.extend(item)
                else:
                    yield item
            
            # Handle persistence with request data
            if all_emails:
                # First convert and save emails
                db_emails = [EmailUtils.email_to_db_email_recursive(email, request) for email in all_emails]
                successful_emails, duplicate_emails, failed_emails = await self.email_repository.bulk_save_emails(db_emails)
                
                self.logger.info("Extracting recipients from successful emails, note that duplicate emails will not have recipients extracted")
                all_recipients = []
                # Match graph emails with their corresponding db emails using source_id
                if successful_emails:
                    all_recipients = EmailUtils.extract_recipients_from_init_response_emails(all_emails, successful_emails)
                    # Save recipients - any failure here will raise an exception
                    if all_recipients:
                        await self.email_recipient_repository.bulk_save_recipients(all_recipients)
                else:
                    self.logger.error("No recipients to save, there are no successful emails")

                # Extract IDs for the response
                successful_email_ids, duplicate_email_ids, failed_email_ids = EmailUtils.extract_email_ids_from_results(
                    successful_emails, duplicate_emails, failed_emails
                )
                
                total_emails = len(successful_email_ids) + len(duplicate_email_ids) + len(failed_email_ids)

                yield {
                    "status": "persistence_complete",
                    "message": f"Emails: {len(successful_emails)} saved, {len(duplicate_emails)} duplicates, {len(failed_emails)} failed.",
                    "data": {
                        "total_emails": total_emails,
                        "successful": successful_email_ids,
                        "duplicates": duplicate_email_ids,
                        "failures": failed_email_ids
                    }
                }
                return  # Successfully completed

            # Only raise exception if no emails were found
            yield {"status": "warning", "message": "No emails were found to process"}
            raise RecursiveEmailException(
                detail="Failed to recursively retrieve emails, no emails were retrieved.",
                folder_id=folder_id,
                status_code=500
            )

        except APIError as e:
            self.logger.error("API Error in get_all_emails_recursively: %s", str(e))
            raise  # Use bare raise here to preserve the original exception context
        except EmailPersistenceException as e:
            self.logger.warning("No emails were saved: %s", str(e))
            yield {"status": "error", "message": f"No emails were saved: {str(e)}"}
            raise e
        except Exception as e:
            self.logger.error(
                "Unexpected error during recursive email retrieval for folder %s: %s",
                folder_id,
                str(e)
            )
            yield {"status": "error", "message": f"Failed to recursively retrieve emails: {str(e)}"}
            raise RecursiveEmailException(
                detail=f"Failed to recursively retrieve emails: {str(e)}",
                folder_id=folder_id,
                status_code=500
            ) from e




    async def _get_all_emails_recursively_internal(
        self, 
        folder_id: str
    ) -> AsyncGenerator[Union[List[Email], Dict[str, Any]], None]:
        """
        Internal method that handles the recursive traversal of folders and email retrieval.
        """
        try:
            # Get all subfolders
            folder = await self.folder_service.get_folder(folder_id) # track current folder
            subfolders = await self.folder_service.get_child_folders(folder_id)

            # Check cache and get new emails
            cached_info = self.email_cache_service.get_cache_info(folder_id)
            cached_emails = []
            if cached_info:
                self.logger.info("Found cached emails for folder %s", folder_id)
                cached_emails = list(self.email_cache_service.cache[folder_id].emails.values())
                yield {"status": "progress", "message": f"Retrieved {len(cached_emails)} emails from cache", "folder_id": folder_id}

            # Always check for new emails
            new_emails = []
            async for item in self.email_collection_service.get_all_emails_by_folder_id(folder_id):
                if isinstance(item, list):
                    # Filter out emails that are already in cache
                    if cached_emails:
                        cached_ids = {email.source_id for email in cached_emails}
                        new_emails = [email for email in item if email.source_id not in cached_ids]
                        if new_emails:
                            self.logger.info("Found %d new emails in folder %s", len(new_emails), folder_id)
                            # Update cache with new emails
                            all_emails = cached_emails + new_emails
                            self.email_cache_service.store_folder_emails(folder_id, all_emails)
                            yield {"status": "progress", "message": f"Found {len(new_emails)} new emails", "folder_id": folder_id}
                    else:
                        new_emails = item
                        self.email_cache_service.store_folder_emails(folder_id, new_emails)
                        yield {"status": "progress", "message": f"Retrieved {len(new_emails)} emails", "folder_id": folder_id}
                else:
                    yield item

            # Yield combined emails from this folder
            all_folder_emails = cached_emails + new_emails
            if all_folder_emails:
                yield all_folder_emails
            
            # Recursively get emails from all subfolders
            for folder in subfolders:
                try:
                    async for item in self._get_all_emails_recursively_internal(folder.id):
                        yield item
                except APIError as e:
                    self.logger.error("API Error in _get_all_emails_recursively_internal for folder %s: %s", folder_id, str(e))
                    raise  # Let it propagate to parent for global handling
                except (FolderException, EmailException) as e:
                    self.logger.warning(
                        "Skipping problematic subfolder %s: %s",
                        folder.id,
                        str(e)
                    )
                    continue
                    
        except (FolderException, EmailException) as e:
            self.logger.error("Error processing folder %s: %s", folder_id, str(e))
            raise