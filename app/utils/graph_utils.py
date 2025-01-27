import logging
from typing import List, Dict, Any, TypeVar, Type

from msgraph.generated.users.item.translate_exchange_ids.translate_exchange_ids_post_request_body import (
    TranslateExchangeIdsPostRequestBody,
)
from msgraph.generated.models.exchange_id_format import ExchangeIdFormat

from app.exception.exceptions import (
    FolderException,
    AuthenticationFailedException,
    GraphResponseException,
    IdTranslationException,
)
from app.service.graph_service import Graph

logger = logging.getLogger(__name__)

T = TypeVar("T")

"""
SUMMARY: 
This class serves as a utility class for all graph operations that are not directly tied 
to an entity in this code base.
"""


class GraphUtils:
    def __init__(self, graph: Graph):
        self.graph = graph

    async def get_folder_id_by_name(self, folder_name: str) -> str:
        """
        Retrieve the folder ID for a given folder name from the Graph API.

        Args:
            folder_name (str): The name of the folder to find.

        Returns:
            str: The ID of the found folder.

        Raises:
            AuthenticationFailedException: If the client is not authenticated
            FolderException: If the folder is not found or there's an error retrieving it
        """
        try:
            auth_status = self.graph.ensure_authenticated()
            if not auth_status.get("authenticated"):
                raise AuthenticationFailedException(
                    detail=f"Graph client not authenticated. Redirect user to: {auth_status['auth_url']}"
                )

            mail_folders = await self.graph.client.me.mail_folders.get()
            for folder in mail_folders.value:
                if folder.display_name.lower() == folder_name.lower():
                    return folder.id

            # Folder not found, raise an exception
            raise FolderException(
                detail=f"Folder '{folder_name}' not found",
                folder_name=folder_name,
                status_code=404,
            )

        except AuthenticationFailedException:
            logger.error("Authentication failed")
            raise
        except FolderException:
            logger.error("Folder '%s' not found", folder_name)
            raise
        except Exception as e:
            logger.error("Error retrieving folder ID for '%s': %s", folder_name, e)
            raise FolderException(
                detail=f"Failed to retrieve folder: {str(e)}",
                folder_name=folder_name,
                status_code=500,
            ) from e

    async def translate_ids(self, input_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Translate regular IDs to immutable IDs for emails using the SDK's built-in translate_exchange_ids method.

        Args:
            input_ids (List[str]): List of input IDs to translate.

        Returns:
            List[Dict[str, Any]]: Translated IDs with source and target mapping.
        """
        try:
            if not input_ids:
                raise IdTranslationException(
                    detail="No input IDs to translate", status_code=400
                )

            self.graph.ensure_authenticated()
            request_body = TranslateExchangeIdsPostRequestBody(
                input_ids=input_ids,
                source_id_type=ExchangeIdFormat.RestId,
                target_id_type=ExchangeIdFormat.RestImmutableEntryId,
            )

            result = await self.graph.client.me.translate_exchange_ids.post(request_body)
            return [
                {"source_id": item.source_id, "target_id": item.target_id}
                for item in result.value
            ]

        except IdTranslationException as e:
            logger.error("Error translating IDs: %s", e)
            raise
        except Exception as e:
            logger.error("Error translating IDs: %s", e)
            raise IdTranslationException(
                detail=f"Failed to translate IDs: {str(e)}",
                source_ids=input_ids,
                status_code=500,
            ) from e

    def get_collection_value(self, response: Any, expected_type: Type[T]) -> List[T]:
        """
        Safely extracts the 'value' array from a Graph API collection response.

        Args:
            response: The Graph API response object
            expected_type: The expected collection response type

        Returns:
            List[T]: The collection items

        Raises:
            GraphResponseException: If response is invalid or wrong type
        """
        if not isinstance(response, expected_type):
            raise GraphResponseException(
                detail=f"Invalid response type - expected {expected_type.__name__}",
                response_type=type(response).__name__,
                status_code=500,
            )

        if response.value is None:
            raise GraphResponseException(
                detail="Response missing 'value' property", status_code=500
            )

        return response.value
