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
from app.utils.retry_utils import RetryUtils
from app.models.retries.retry_enums import RetryProfile
from app.models.retries.retry_context import RetryContext






class EmailDownloadService:
    def __init__(self, graph: Graph, graph_translator: GraphIDTranslator):
        self.graph = graph
        self.graph_translator = graph_translator
        self.logger = logging.getLogger(__name__)
        self.retry_utils = RetryUtils(retry_profile=RetryProfile.BATCH)
        
        # Configurable parameters
        self.config = {
            'page_size': 50,
            'translation_batch_size': 1000,
            'email_chunk_size': 100,
            'max_concurrent_requests': 5,
            'max_retries': 3,
            'retry_delay': 2
        }






    def __start_metrics(self) -> BatchMetrics:
        # Initialize metrics and start overall processing timer.
        metrics = BatchMetrics(start_time=time.time())
        metrics.start_processing()
        return metrics






    async def get_all_emails_by_folder_id(self, folder_id: str) -> AsyncGenerator[Union[List[Email], Dict[str, Any]], None]:
        """
        Retrieve all emails from a folder with optimized batch processing and progress updates.
        
        Yields:
            - Progress updates (as dict) for the frontend (via get_progress_info())
            - Finally, the list of Email objects.
        """
        metrics = self.__start_metrics()
        
        try:
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

        except Exception as e:
            self.logger.error("Error retrieving emails from folder %s: %s", folder_id, str(e))
            raise EmailException(detail=str(e), status_code=500) from e






    async def _fetch_messages(self, folder_id: str, metrics: BatchMetrics) -> AsyncGenerator[Union[List[Any], Dict[str, Any]], None]:
        """
        Fetch all messages from a folder.
        
        Yields progress info from the metrics along with phase information.
        """
        metrics.current_phase = "fetching"
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
        Process messages into Email objects in chunks.
        
        Yields progress updates (including phase info) to inform the frontend.
        """
        try:
            metrics.current_phase = "processing"
            yield metrics.get_progress_info()  # phase "processing"
            
            emails = []
            metrics.start_processing()
            for i in range(0, len(messages), self.config['email_chunk_size']):
                chunk = messages[i:i + self.config['email_chunk_size']]
                chunk_emails = [
                    Email.from_graph_message(msg, id_mapping[msg.id])
                    for msg in chunk if msg.id in id_mapping
                ]
                emails.extend(chunk_emails)
                metrics.emails_processed += len(chunk_emails)
                yield metrics.get_progress_info()  # updated progress within processing phase
            metrics.end_processing()
            yield emails
        finally:
            # Log a single final metrics summary to the console.
            metrics.log_final_metrics(self.logger)







    async def _fetch_single_page(self, folder_id: str,
                                 page_num: int, 
                                 metrics: BatchMetrics,
                                 get_count: bool = False) -> Tuple[List[Any], Optional[int]]:
        """
        Fetch a single page of messages from the specified folder.
        
        Uses retry logic via RetryContext and records page timing metrics.
        """
        start_time = 0  # Define start_time for use in the nested function
        async def fetch():
            nonlocal start_time
            start_time = time.time()
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
            return messages, total_count

        retry_context = RetryContext(
            operation=fetch,
            error_msg=f"Error fetching page {page_num}",
            metrics_recorder=lambda: metrics.record_page_retry() if metrics else None,
            error_recorder=lambda: metrics.record_page_error() if metrics else None,
            custom_exception=EmailException
        )
        return await self.retry_utils.retry_operation(retry_context)







    async def _fetch_all_pages(self, folder_id: str, total_pages: int, metrics: BatchMetrics) -> List[Any]:
        """
        Fetch all remaining pages concurrently with controlled concurrency.
        
        Updates metrics and returns a flattened list of messages.
        """
        async def fetch_with_semaphore(sem, page_num):
            async with sem:
                messages, _ = await self._fetch_single_page(folder_id, page_num, metrics, get_count=False)
                return messages

        sem = asyncio.Semaphore(self.config['max_concurrent_requests'])
        # Pages 1 to total_pages-1 (page 0 already fetched)
        tasks = [fetch_with_semaphore(sem, i) for i in range(1, total_pages)]
        if not tasks:
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
        id_mapping = {}
        batch_size = self.config['translation_batch_size']
        for i in range(0, len(message_ids), batch_size):
            current_batch = message_ids[i:i + batch_size]
            batch_range = f"{i}-{i + batch_size}"
            
            async def translate(batch=current_batch):
                return await self.graph_translator.translate_ids(batch)
            
            retry_context = RetryContext(
                operation=translate,
                error_msg=f"Error translating batch {batch_range}",
                metrics_recorder=lambda: metrics.record_translation_retry() if metrics else None,
                error_recorder=lambda: metrics.record_translation_error() if metrics else None,
                custom_exception=IdTranslationException
            )
            
            try:
                results = await self.retry_utils.retry_operation(retry_context)
                for item in results:
                    id_mapping[item["source_id"]] = item["target_id"]
                metrics.ids_translated += len(results)
            except IdTranslationException as e:
                self.logger.error("Failed to translate batch %s: %s", batch_range, str(e))
                continue
                
        return id_mapping
