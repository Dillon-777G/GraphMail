from typing import List
from fastapi import HTTPException

class IdTranslationException(HTTPException):
    """
    Exception raised when there's an error translating source IDs to immutable IDs.

    Current use cases:
    - Translating message(EMAIL) IDs to immutable IDs
    """
    def __init__(self, detail: str = "Failed to translate message IDs", source_ids: List[str] = None, status_code: int = 500):
        """
        Initialize the exception.

        Args:
            detail (str): A detailed error message.
            source_ids (List[str]): The IDs that failed to translate.
            status_code (int): The HTTP status code (default: 500 Internal Server Error).
        """
        super().__init__(status_code=status_code, detail=detail)
        self.source_ids = source_ids or [] 