# Third party imports
from fastapi import HTTPException

class RecursiveEmailException(HTTPException):
    """Exception raised when there's an error during recursive email retrieval operations."""
    
    def __init__(
        self,
        detail: str,
        folder_id: str | None = None,
        status_code: int = 500
    ):
        """
        Initialize the RecursiveEmailException.
        
        Args:
            detail (str): Detailed error message
            folder_id (str | None): ID of the folder where the error occurred
            status_code (int): HTTP status code (default: 500)
        """
        super().__init__(detail=detail, status_code=status_code)
        self.folder_id = folder_id

    def __str__(self) -> str:
        """Return string representation of the exception."""
        folder_info = f" (Folder ID: {self.folder_id})" if self.folder_id else ""
        return f"{self.detail}{folder_info}" 