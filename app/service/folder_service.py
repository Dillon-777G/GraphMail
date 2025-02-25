import logging
from typing import List

from msgraph.generated.models.mail_folder_collection_response import MailFolderCollectionResponse
from msgraph.generated.users.item.mail_folders.mail_folders_request_builder import MailFoldersRequestBuilder

from kiota_abstractions.base_request_configuration import RequestConfiguration

from app.models.folder import Folder
from app.utils.graph_utils import GraphUtils
from app.service.graph.graph_authentication_service import Graph
from app.error_handling.exceptions.folder_exception import FolderException
from app.error_handling.exceptions.graph_response_exception import GraphResponseException
from app.service.retry_service import RetryService
from app.models.retries.retry_context import RetryContext
from app.models.retries.retry_enums import RetryProfile
from app.models.metrics.folder_metrics import FolderMetrics


"""
SUMMARY:
I have elected to not parallelize the folder retrieval. It is less likely to be a bottleneck
than the email retrieval. If we introduce too much parallelization, we may overwhelm the
Graph API and cause rate limiting, less than ideal.

I have tested this with 10 nested folders, and it performed well. I do not expect our users to be
using more than 10 levels of folders, so I believe our current implementation is sufficient. 

AGAIN: Our heaviest bottleneck is the email retrieval, not the folder retrieval.
"""
class FolderService:
    def __init__(self, graph: Graph):
        self.graph = graph
        self.logger = logging.getLogger(__name__)
        self.retry_service = RetryService(retry_profile=RetryProfile.STANDARD)




    def __start_metrics(self) -> FolderMetrics:
        """Initialize metrics for folder operations"""
        metrics = FolderMetrics()
        metrics.start_processing()
        return metrics




    async def get_root_folders(self) -> List[Folder]:
        metrics = self.__start_metrics()
        
        try:
            folders = await self.retry_service.retry_operation(
                RetryContext(
                    operation=self.__fetch_root_folders,
                    error_msg="Failed to retrieve root folders",
                    custom_exception=FolderException
                )
            )
            
            # Just pass the child_folder_count from each folder
            metrics.record_retrieval(len(folders))
            return folders

        except GraphResponseException as e:
            self.logger.error("Graph API error retrieving root folders: %s", str(e))
            metrics.record_retrieval_failure("root", str(e))
            raise
        except Exception as e:
            self.logger.error("Error retrieving root folders: %s", str(e))
            metrics.record_retrieval_failure("root", str(e))
            raise FolderException(
                detail=f"Failed to retrieve root folders: {str(e)}",
                status_code=500
            ) from e
        finally:
            metrics.end_processing()
            metrics.current_phase = "complete"
            metrics.log_metrics_retrieval(self.logger, "Get Root Folders")




    async def get_child_folders(self, folder_id: str) -> List[Folder]:
        """
        Get all child folders for a specific folder ID.
        """
        metrics = self.__start_metrics()
        
        try:
            folders = await self.retry_service.retry_operation(
                RetryContext(
                    operation=lambda: self.__fetch_child_folders(folder_id),
                    error_msg=f"Failed to retrieve child folders for folder {folder_id}",
                    custom_exception=lambda detail, status_code: FolderException(
                        detail=detail,
                        folder_id=folder_id,
                        status_code=status_code
                    )
                )
            )
            
            # Only process metrics if we found child folders
            if folders:
                for folder in folders:
                    metrics.record_retrieval(folder.child_folder_count, folder.id, folder.parent_folder_id, folder.display_name)
                metrics.end_processing()
                metrics.current_phase = "complete"
                metrics.log_metrics_retrieval(self.logger, "Get Child Folders")
                
            return folders

        except Exception as e:
            self.logger.error("Error retrieving child folders for folder ID %s: %s", folder_id, str(e))
            metrics.record_retrieval_failure(folder_id, str(e))
            metrics.end_processing()
            metrics.current_phase = "error"
            metrics.log_metrics_retrieval(self.logger, "Get Child Folders")
            raise FolderException(
                detail=f"Failed to retrieve child folders: {str(e)}",
                folder_id=folder_id,
                status_code=500
            ) from e




    async def get_folder(self, folder_id: str) -> Folder:
        """
        Get details of a specific folder by its ID.
        """
        metrics = self.__start_metrics()  # This returns an instance of FolderMetrics.
        
        try:
            folder = await self.retry_service.retry_operation(
                RetryContext(
                    operation=lambda: self.graph.client.me.mail_folders.by_mail_folder_id(folder_id).get(),
                    error_msg=f"Failed to retrieve folder {folder_id}",
                    custom_exception=lambda detail, status_code: FolderException(
                        detail=detail,
                        folder_id=folder_id,
                        status_code=status_code
                    )
                )
            )
            folder = Folder.from_graph_folder(folder)
            metrics.record_retrieval(folder.child_folder_count, folder.id, folder.parent_folder_id, folder.display_name)
            self.logger.info("Retrieved folder: %s", folder.display_name)
            return folder

        except Exception as e:
            self.logger.error("Error retrieving folder %s: %s", folder_id, e)
            metrics.record_retrieval_failure(folder_id, str(e))
            raise FolderException(
                detail=f"Failed to retrieve folder: {str(e)}",
                folder_id=folder_id,
                status_code=500
            ) from e
        finally:
            metrics.end_processing()
            metrics.current_phase = "complete"
            metrics.log_metrics_retrieval(self.logger, "Get Folder")
                




    # Helper methods for the actual fetching
    async def __fetch_root_folders(self):
        result = await self.graph.client.me.mail_folders.get(
            request_configuration=RequestConfiguration(
                query_parameters=MailFoldersRequestBuilder.MailFoldersRequestBuilderGetQueryParameters(
                    top=200
                )
            )
        )
        return [
            Folder.from_graph_folder(folder)
            for folder in GraphUtils.get_collection_value(
                result, MailFolderCollectionResponse
            )
        ]

    async def __fetch_child_folders(self, folder_id: str):
        result = await (
            self.graph.client.me.mail_folders
            .by_mail_folder_id(folder_id)
            .child_folders.get(
                request_configuration=RequestConfiguration(
                    query_parameters=MailFoldersRequestBuilder.MailFoldersRequestBuilderGetQueryParameters(
                        top=200
                    )
                )
            )
        )
        return [
            Folder.from_graph_folder(folder)
            for folder in GraphUtils.get_collection_value(result, MailFolderCollectionResponse)
        ]