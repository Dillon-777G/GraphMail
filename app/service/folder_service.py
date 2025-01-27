
import logging
from typing import List

from msgraph.generated.models.mail_folder_collection_response import MailFolderCollectionResponse

from app.models.folder import Folder
from app.utils.graph_utils import GraphUtils
from app.exception.exceptions import FolderException, GraphResponseException

logger = logging.getLogger(__name__)

class FolderService:
    def __init__(self, graph_utils: GraphUtils):
        self.graph_utils = graph_utils

    async def get_root_folders(self) -> List[Folder]:
        """
        List all root mail folders in the user's mailbox.
        
        Returns:
            List[Folder]: List of root level folders
            
        Raises:
            FolderException: If folders cannot be retrieved
        """
        try:
            result = await self.graph_utils.graph.client.me.mail_folders.get()
            folders = [
                Folder.from_graph_folder(folder)
                for folder in self.graph_utils.get_collection_value(
                    result, MailFolderCollectionResponse
                )
            ]
            
            logger.info("Retrieved %d root folders", len(folders))
            return folders

        except GraphResponseException as e:
            logger.error("Invalid or unexpected response for root folders: %s", e)
            raise e
        except Exception as e:
            logger.error("Error retrieving root folders: %s", e)
            raise FolderException(
                detail=f"Failed to retrieve root folders: {str(e)}",
                status_code=500
            ) from e

    async def get_child_folders(self, folder_id: str) -> List[Folder]:
        """
        Get all child folders for a specific folder ID.
        
        Args:
            folder_id: The ID of the parent folder
            
        Returns:
            List[Folder]: List of child folders
            
        Raises:
            FolderException: If folders cannot be retrieved
        """
        try:
            result = await (
                self.graph_utils.graph.client.me.mail_folders
                .by_mail_folder_id(folder_id)
                .child_folders.get()
            )
            folders = [
                Folder.from_graph_folder(folder)
                for folder in self.graph_utils.get_collection_value(result, MailFolderCollectionResponse)
            ]
            
            logger.info("Retrieved %d child folders for folder ID: %s", len(folders), folder_id)
            return folders

        except GraphResponseException as e:
            logger.error("Invalid or unexpected response for folder ID %s: %s", folder_id, e)
            raise e
        except Exception as e:
            logger.error("Error retrieving child folders for folder ID %s: %s", folder_id, e)
            raise FolderException(
                detail=f"Failed to retrieve child folders: {str(e)}",
                folder_id=folder_id,
                status_code=500
            ) from e

    async def get_folder(self, folder_id: str) -> Folder:
        """
        Get details of a specific folder by its ID.
        
        Args:
            folder_id: The ID of the folder to retrieve
            
        Returns:
            Folder: The requested folder's details
            
        Raises:
            FolderException: If folder cannot be retrieved
        """
        try:
            result = await self.graph_utils.graph.client.me.mail_folders.by_mail_folder_id(folder_id).get()
            folder = Folder.from_graph_folder(result)
            logger.info("Retrieved folder: %s", folder.display_name)
            return folder

        except Exception as e:
            logger.error("Error retrieving folder %s: %s", folder_id, e)
            raise FolderException(
                detail=f"Failed to retrieve folder: {str(e)}",
                folder_id=folder_id,
                status_code=500
            ) from e
