from typing import List, Any, Dict, Union, AsyncGenerator, Tuple, Optional
import logging
import time
import asyncio

from msgraph.generated.users.item.messages.messages_request_builder import MessagesRequestBuilder
from msgraph.generated.models.message_collection_response import MessageCollectionResponse
from kiota_abstractions.base_request_configuration import RequestConfiguration

from app.utils.graph_utils import GraphUtils
from app.service.graph.graph_authentication_service import Graph
from app.service.graph.graph_id_translation_service import GraphIDTranslator
from app.models.email import Email
from app.error_handling.exceptions.email_exception import EmailException
from app.error_handling.exceptions.id_translation_exception import IdTranslationException
from app.models.metrics.batch_metrics import BatchMetrics
from app.service.retry_service import RetryService
from app.models.retries.retry_enums import RetryProfile
from app.models.retries.retry_context import RetryContext





"""
Summary:
This class handles the retrieval from graph api and the processing of emails into our domain objects.
It yields information up to the recursive email service. 
"""
class EmailCollectionService:
    def __init__(self, graph: Graph, graph_translator: GraphIDTranslator):
        self.graph = graph
        self.graph_translator = graph_translator
        self.logger = logging.getLogger(__name__)
        self.retry_service = RetryService(retry_profile=RetryProfile.STANDARD)
        
        # Configurable parameters
        self.config = {
            'page_size': 50,
            'translation_batch_size': 1000,
            'email_chunk_size': 100,
            'max_concurrent_requests': 5,
            'max_retries': 3,
            'retry_delay': 2
        }


    

    async def get_all_emails_by_folder_id(self, folder_id: str) -> AsyncGenerator[Union[List[Email], Dict[str, Any]], None]:
        """
        Retrieve all emails from a folder with optimized batch processing and progress updates.
        
        This method orchestrates the complete email retrieval workflow:
        1. Fetches messages in batches from Microsoft Graph API
        2. Translates Graph message IDs to database IDs
        3. Processes raw messages into domain Email objects
        4. Provides real-time progress updates throughout the process
        
        Yields:
            - Progress updates (as dict) during processing for frontend display
            - Final list of Email objects when complete
            
        Args:
            folder_id: Microsoft Graph ID of the folder to retrieve emails from
            
        Raises:
            EmailException: Wraps any errors that occur during the process
        """
        metrics = self.__start_metrics()
        metrics.folder_id = folder_id
        
        try:
            self.logger.info("Starting email download service for folder: %s", folder_id)
            messages = []
            # Fetch messages (with progress updates and phase info)
            async for result in self._fetch_messages(folder_id, metrics):
                if isinstance(result, list):
                    messages = result
                else:
                    yield result
            if not messages:
                return
            
            # Translate message IDs (with progress updates and phase info)
            id_mapping = {}
            async for result in self._translate_ids(messages, metrics):
                if isinstance(result, dict):
                    id_mapping = result
                else:
                    yield result

            # Process messages into Email objects (with progress updates and phase info)
            async for result in self._process_emails(messages, id_mapping, metrics):
                yield result
            self.logger.info("Email download service completed for folder: %s", folder_id)

        except Exception as e:
            self.logger.error("Error retrieving emails from folder %s: %s", folder_id, str(e))
            raise EmailException(detail=str(e), status_code=500) from e






    async def _fetch_messages(self, folder_id: str, metrics: BatchMetrics) -> AsyncGenerator[Union[List[Any], Dict[str, Any]], None]:
        """
        Fetch all messages from a folder.
        
        Yields progress info from the metrics along with phase information.
        """
        metrics.current_phase = "fetching"
        self.logger.info("Fetching first page of messages for folder: %s", folder_id)
        first_page_messages, total_count = await self._fetch_single_page(folder_id, 0, metrics, get_count=True)
        metrics.total_count = total_count
        metrics.pages_fetched += 1
        yield metrics.get_progress_info()  # includes phase = "fetching"

        if not first_page_messages:
            yield []
            return

        total_pages = (total_count + self.config['page_size'] - 1) // self.config['page_size']
        remaining_messages = await self._fetch_all_pages(folder_id, total_pages, metrics)
        yield first_page_messages + remaining_messages






    async def _translate_ids(self, messages: List[Any], metrics: BatchMetrics) -> AsyncGenerator[Union[Dict[str, str], Dict[str, Any]], None]:
        """
        Translate message IDs to immutable IDs.
        
        Yields progress info (including current phase) before and after translation.
        """
        metrics.current_phase = "translating"
        yield metrics.get_progress_info()  # phase "translating"

        message_ids = [msg.id for msg in messages if msg.id]
        metrics.start_translation()
        id_mapping = await self._translate_message_ids(message_ids, metrics)
        metrics.end_translation()
        yield id_mapping






    async def _process_emails(self, messages: List[Any], id_mapping: Dict[str, str], metrics: BatchMetrics) -> AsyncGenerator[Union[List[Email], Dict[str, Any]], None]:
        """
        Process Graph API messages into Email objects in manageable chunks.
        
        This method:
        1. Converts raw Graph API message objects into domain Email objects
        2. Processes messages in configurable chunks to avoid memory issues
        3. Uses ID mapping to associate Graph message IDs with database IDs
        4. Tracks metrics throughout the processing
        5. Yields progress updates to inform the frontend during processing
        6. Finally yields the complete list of processed Email objects
        
        Args:
            messages: List of raw message objects from Microsoft Graph API
            id_mapping: Dictionary mapping Graph message IDs to database IDs
            metrics: BatchMetrics object for tracking performance and progress
            
        Yields:
            - Progress information dictionaries during processing
            - Final list of Email objects when processing is complete
            
        Raises:
            Exception: Any exceptions during processing are logged and re-raised
            
        Note:
            Messages without corresponding entries in id_mapping will be skipped.
            This can happen if ID translation failed for some messages.
        """
        total_messages = len(messages)
        chunk_size = self.config['email_chunk_size']
        total_chunks = (total_messages + chunk_size - 1) // chunk_size

        try:
            metrics.current_phase = "processing"
            self.logger.info("Starting email processing phase for %d messages", total_messages)
            yield metrics.get_progress_info()  # phase "processing"
            
            emails = []
            metrics.start_processing()
            for i in range(0, total_messages, chunk_size):
                chunk_num = i // chunk_size + 1
                chunk_end = min(i + chunk_size, total_messages)
                self.logger.info("_process_emails: intializing processing of chunk %d/%d (messages %d-%d)", 
                            chunk_num, total_chunks, i, chunk_end-1)
                chunk = messages[i:i + chunk_size]
                
                chunk_emails = [
                    Email.from_graph_message(msg, id_mapping[msg.id])
                    for msg in chunk if msg.id in id_mapping
                ]
                emails.extend(chunk_emails)
                metrics.emails_processed += len(chunk_emails)

                self.logger.info("_process_emails: Processed %d/%d emails in chunk %d", 
                           len(chunk_emails), len(chunk), chunk_num)

                yield metrics.get_progress_info()  # updated progress within processing phase
            metrics.end_processing()
            yield emails
        except Exception as e:
            self.logger.error("_process_emails: Error during email processing: %s", str(e))
            raise EmailException(detail=f"Error during email processing: {str(e)}", status_code=500) from e
        finally:
            # Log a single final metrics summary to the console.
            metrics.log_final_metrics(self.logger)







    async def _fetch_single_page(self, folder_id: str,
                                 page_num: int, 
                                 metrics: BatchMetrics,
                                 get_count: bool = False) -> Tuple[List[Any], Optional[int]]:
        """
        Fetch a single page of messages from the specified folder in Microsoft Graph API.
        
        Constructs a Graph API request with attachment data, selected fields, pagination,
        and optional count. Implements retry logic and records performance metrics.
        
        Args:
            folder_id: Mail folder Graph ID to query
            page_num: Zero-based page number to fetch
            metrics: Object for tracking performance metrics
            get_count: Whether to request total count (should only be true for first page)
        
        Returns:
            Tuple of (message list, total count or None)
        
        Raises:
            EmailException: If all retries fail
        """
        start_time = 0  # Define start_time for use in the nested function
        async def fetch():
            nonlocal start_time
            start_time = time.time()
            self.logger.info("Starting fetch of page %d of messages for folder: %s", page_num, folder_id)
            page_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
                expand=["attachments"],
                select=[
                    'bccRecipients', 'body', 'ccRecipients', 'conversationId',
                    'from', 'hasAttachments', 'id', 'isRead', 'receivedDateTime',
                    'subject', 'toRecipients'
                ],
                top=self.config['page_size'],
                skip=page_num * self.config['page_size'],
                count=get_count
            )
            page_config = RequestConfiguration(query_parameters=page_params)
            result = await self.graph.client.me.mail_folders.by_mail_folder_id(
                folder_id
            ).messages.get(request_configuration=page_config)
            messages = GraphUtils.get_collection_value(result, MessageCollectionResponse)
            total_count = getattr(result, 'odata_count', None) if get_count else None
            duration = time.time() - start_time
            if metrics:
                metrics.record_page_time(duration, len(messages))
            self.logger.info("Fetched page %d of messages for folder: %s in %s seconds", page_num, folder_id, duration)
            return messages, total_count

        retry_context = RetryContext(
            operation=fetch,
            error_msg=f"Error fetching page {page_num}",
            metrics_recorder=lambda: metrics.record_page_retry() if metrics else None,
            error_recorder=lambda: metrics.record_page_error() if metrics else None,
            custom_exception=EmailException
        )
        return await self.retry_service.retry_operation(retry_context)







    async def _fetch_all_pages(self, folder_id: str, total_pages: int, metrics: BatchMetrics) -> List[Any]:
        """
        Fetch all remaining pages concurrently with controlled concurrency.
        
        Updates metrics and returns a flattened list of messages.
        """
        self.logger.info("Starting fetch of all remaining pages for folder: %s", folder_id)

        # If there's only one page (or somehow less), log this but don't treat as error
        if total_pages <= 1:
            self.logger.info("No additional pages to fetch for folder: %s (total_pages=%d)", 
                            folder_id, total_pages)
            return []

        async def fetch_with_semaphore(sem, page_num):
            async with sem:
                messages, _ = await self._fetch_single_page(folder_id, page_num, metrics, get_count=False)
                return messages

        sem = asyncio.Semaphore(self.config['max_concurrent_requests'])
        # Pages 1 to total_pages-1 (page 0 already fetched)
        tasks = [fetch_with_semaphore(sem, i) for i in range(1, total_pages)]
        if not tasks:
            self.logger.warning("No remaining pages to fetch for folder: %s", folder_id)
            return []

        pages = await asyncio.gather(*tasks)
        metrics.pages_fetched += len([page for page in pages if page])
        # Flatten the list of pages into a single list of messages
        return [msg for page in pages if page for msg in page]






    async def _translate_message_ids(self, message_ids: List[str], metrics: BatchMetrics) -> Dict[str, str]:
        """
        Translate message IDs in batches with retry logic.
        
        Returns a mapping of source IDs to translated IDs.
        """
        self.logger.info("Starting translation of %d message IDs", len(message_ids))

        id_mapping = {}
        batch_size = self.config['translation_batch_size']
        total_batches = (len(message_ids) + batch_size - 1) // batch_size

        # Process the message IDs in batches
        for i in range(0, len(message_ids), batch_size):
            current_batch = message_ids[i:i + batch_size]
            batch_num = i // batch_size + 1
            batch_end = min(i + batch_size, len(message_ids))
            self.logger.info("_translate_message_ids: Processing batch %d/%d (IDs %d-%d)", 
                        batch_num, total_batches, i, batch_end-1)
            
            # Define the operation to be retried
            async def translate(batch=current_batch):
                return await self.graph_translator.translate_ids(batch)
            
            # Build the retry context
            retry_context = self._build_retry_context(translate, metrics, batch_num, total_batches)

            # Attempt to translate the batch
            try:
                results = await self.retry_service.retry_operation(retry_context)
                self.logger.info("Successfully translated batch %d/%d: %d IDs processed", 
                           batch_num, total_batches, len(results))

                for item in results:
                    id_mapping[item["source_id"]] = item["target_id"]
                metrics.ids_translated += len(results)
            except IdTranslationException as e:
                self.logger.error("Failed to translate batch %d/%d (%d IDs): %s", 
                            batch_num, total_batches, len(current_batch), str(e))
                continue
                
        return id_mapping


    ##################
    # HELPER METHODS #
    ##################


    def __start_metrics(self) -> BatchMetrics:
        # Initialize metrics and start overall processing timer.
        metrics = BatchMetrics(start_time=time.time())
        metrics.start_processing()
        return metrics    


    def _build_retry_context(self, operation, metrics, batch_num, total_batches):
        return RetryContext(
                operation=operation,
                error_msg=f"Error translating batch {batch_num}/{total_batches}",
                metrics_recorder=lambda: metrics.record_translation_retry() if metrics else None,
                error_recorder=lambda: metrics.record_translation_error() if metrics else None,
                custom_exception=IdTranslationException
            )