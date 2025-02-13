import logging
from typing import Any, TypeVar, List, Type
from app.error_handling.exceptions.graph_response_exception import GraphResponseException

T = TypeVar("T")

"""
SUMMARY: 
This class serves as a utility class for all graph operations that are not directly tied 
to an entity in this code base.
""" 
class GraphUtils:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

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
