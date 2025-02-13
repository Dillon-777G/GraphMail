from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

class EmailPersistenceException(HTTPException):
    """
    Exception raised for email persistence errors.
    
    Attributes:
        detail: Detailed error message
        status_code: HTTP status code
        message_ids: List of message IDs that failed to persist
        original_error: The original database error (if any)
    """
    def __init__(
        self,
        detail: str = "Failed to persist emails",
        status_code: int = 500,
        message_ids: Optional[List[str]] = None,
        original_error: Optional[Exception] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.message_ids = message_ids
        self.original_error = original_error

    def __str__(self) -> str:
        base_msg = f"EmailPersistenceException: {self.detail}"
        if self.message_ids:
            base_msg += f" (Message IDs: {self.message_ids})"
        if self.original_error:
            base_msg += f" (Original error: {str(self.original_error)})"
        return base_msg

    def is_duplicate_error(self) -> bool:
        """
        Check if this exception was caused by a duplicate record error.
        
        Returns:
            bool: True if the error was caused by a duplicate record, False otherwise
        """
        if isinstance(self.original_error, IntegrityError):
            if hasattr(self.original_error, 'orig') and self.original_error.orig is not None:
                # MySQL error code for duplicate entry is 1062
                return getattr(self.original_error.orig, 'args', [None])[0] == 1062
        return False