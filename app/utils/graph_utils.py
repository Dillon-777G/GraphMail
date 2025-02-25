import logging
from typing import Any, TypeVar, List, Type
from app.error_handling.exceptions.graph_response_exception import GraphResponseException

T = TypeVar("T")
logger = logging.getLogger(__name__)

"""
SUMMARY: 
This class serves as a utility class for all graph operations that are not directly tied 
to an entity in this code base.
""" 
class GraphUtils:

    @staticmethod
    def get_collection_value(response: Any, expected_type: Type[T]) -> List[T]:
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
        match response:
            case _ if not response:
                logger.info("Graph response is empty or invalid. \nRESPONSE: %s", str(response))
                raise GraphResponseException(
                    detail=f"Response is empty or invalid.\nRESPONSE: {response}",
                    response_type=type(response).__name__,
                    status_code=500
                )
            case _ if not isinstance(response, expected_type):
                logger.info("Graph response type is invalid. Expected: %s Actual: %s", str(expected_type), str(response))
                raise GraphResponseException(
                    detail=f"Invalid response type - expected {expected_type.__name__}",
                    response_type=type(response).__name__,
                    status_code=500,
                )
            case _ if getattr(response, "value", None) is None:
                logger.info("Graph response value key is missing, uh oh. \nRESPONSE: %s", str(response))
                raise GraphResponseException(
                    detail="Response missing 'value' property",
                    status_code=500
                )
            case _:
                return response.value
