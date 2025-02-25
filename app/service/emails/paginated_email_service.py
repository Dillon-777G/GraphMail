import logging
from typing import Any, Dict, List
from kiota_abstractions.base_request_configuration import RequestConfiguration

from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder
from msgraph.generated.models.message_collection_response import MessageCollectionResponse

from app.utils.graph_utils import GraphUtils

from app.models.email import Email
from app.service.retry_service import RetryService
from app.models.retries.retry_context import RetryContext
from app.models.retries.retry_enums import RetryProfile
from app.models.metrics.paginated_metrics import PaginatedMetrics

from app.error_handling.exceptions.email_exception import EmailException

from app.service.emails.email_cache_service import EmailCacheService
from app.service.graph.graph_authentication_service import Graph

"""
SUMMARY:
This service is responsible for fetching emails for a given folder. Parallel pagination and
batched ID translation are used to improve performance. I have decided to only use parallelization
on the message processing and not the ID translation as the ID translation typically has a lower latency
then the message processing.
"""
class PaginatedEmailService:
    def __init__(self, graph: Graph):
        self.graph = graph
        self.logger = logging.getLogger(__name__)
        # Use STANDARD profile for pagination as it's less aggressive than BATCH
        self.retry_service = RetryService(retry_profile=RetryProfile.STANDARD)
        self.email_cache = EmailCacheService()
        

    def __start_metrics(self) -> PaginatedMetrics:
        """Initialize metrics for paginated operations."""
        metrics = PaginatedMetrics()
        metrics.start_processing()
        metrics.current_page = 0
        metrics.items_per_page = 0  # This should be set when you get the first page
        metrics.total_pages = 0     # This should be calculated when you get total count
        return metrics




    async def get_paginated_emails_by_folder_id(
    self, folder_id: str, page: int = 1, per_page: int = 25, subject: str = None) -> Dict[str, Any]:
        metrics = self.__start_metrics()  # Assume this returns a BatchMetrics instance.
        
        try:
            self.logger.info("""
            Getting paginated emails for folder %s,
            page %s, per_page %s, subject %s",
            folder_id, page, per_page, subject)
            """)

            page = max(1, page)
            per_page = max(1, per_page)
            offset = (page - 1) * per_page

            page_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
                select=['bccRecipients', 'body', 'ccRecipients', 'conversationId', 
                        'from', 'hasAttachments', 'id', 'isRead', 'receivedDateTime', 
                        'subject', 'toRecipients'],
                top=per_page,
                skip=offset,
                count=True,
                filter=f"contains(subject, '{subject}')" if subject else '',
                expand=["attachments"]
            )
            page_config = RequestConfiguration(query_parameters=page_params)
            
        
            retry_context = RetryContext(
                operation=lambda: self.graph.client.me.mail_folders.by_mail_folder_id(
                    folder_id
                ).messages.get(request_configuration=page_config),
                error_msg=f"Error fetching paginated emails from folder {folder_id} on page {page}",
                custom_exception=EmailException
            )


            result = await self.retry_service.retry_operation(retry_context)
            messages = GraphUtils.get_collection_value(result, MessageCollectionResponse)
            total = getattr(result, 'odata_count', len(messages))
            total_pages = (total + per_page - 1) // per_page
            emails = [Email.from_graph_message_without_id(msg) for msg in messages]
            email_count = len(emails)
            self.email_cache.store_folder_emails(folder_id, emails) # here we are calling the cache service to store the emails
            
            return {
                "data": emails,
                "elements_on_page": email_count,
                "total_elements": total,
                "total_pages": total_pages,
                "metrics": metrics.get_progress_info()
            }

        except Exception as e:
            self.logger.error("Error retrieving paginated emails from folder %s: %s", folder_id, str(e))
            raise EmailException(detail=str(e), status_code=500) from e
        finally:
            metrics.emails_processed = len(messages) if messages else None
            metrics.total_count = total
            metrics.current_phase = "complete" if total > 0 else "complete with empty result"
            metrics.current_page = page if total_pages > 0 else 0
            metrics.items_per_page = per_page if total > 0 else 0
            metrics.total_pages = total_pages
            metrics.end_processing()
            metrics.log_final_metrics(self.logger)  # Using a final summary method similar to BatchMetrics.

        
    async def get_cached_emails_by_ids(
        self, folder_id: str, source_ids: List[str]) -> List[Email]:
        """
        Try to retrieve emails from cache first, fallback to API if needed
        
        Args:
            folder_id: The ID of the folder
            source_ids: List of source IDs to retrieve
            
        Returns:
            List[Email]: The requested emails
            
        Raises:
            EmailException: If emails cannot be retrieved
        """
        # Try cache first
        self.logger.info("Attempting to get cached emails for folder %s, source_ids %s", folder_id, source_ids)
        cached_emails = self.email_cache.get_emails_by_ids(folder_id, source_ids)
        if cached_emails and len(cached_emails) == len(source_ids):
            self.logger.info("Retrieved %d emails from cache for folder %s", len(cached_emails), folder_id)
            return cached_emails
            
        # If cache miss or partial hit, fetch the page again
        self.logger.info("Cache miss for folder %s, fetching from API", folder_id)
        result = await self.get_paginated_emails_by_folder_id(folder_id)
        emails = result["data"]
        
        # Create a map of source_id to Email object
        email_map = {email.source_id: email for email in emails}
        
        # Get requested emails
        found_emails = []
        for msg_id in source_ids:
            if msg_id in email_map:
                found_emails.append(email_map[msg_id])
            else:
                self.logger.warning("Message %s not found in folder %s", msg_id, folder_id)
                
        return found_emails
