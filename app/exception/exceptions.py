from typing import List
from fastapi import HTTPException

"""
SUMMARY: Due to the micro-service nature of this architecture, 
all custom exceptions should be defined here to keep a single
point of access. 
"""

class AuthenticationFailedException(HTTPException):
    """
    Exception raised for authentication-related issues during token exchange.
    """
    def __init__(self, detail: str = "Authentication failed", status_code: int = 401):
        """
        Initialize the exception.

        Args:
            detail (str): A detailed error message.
            status_code (int): The HTTP status code (default: 401 Unauthorized).
        """
        super().__init__(status_code=status_code, detail=detail)


class EmailAttachmentException(HTTPException):
    """
    Exception raised for invalid or unsupported attachments.
    """
    def __init__(self, detail: str = "Invalid attachment", attachment_id: str = None, status_code: int = 400):
        """
        Initialize the exception.

        Args:
            detail (str): A detailed error message.
            attachment_id (str): The ID of the attachment (optional).
            status_code (int): The HTTP status code (default: 400 Bad Request).
        """
        super().__init__(status_code=status_code, detail=detail)
        self.attachment_id = attachment_id


class FolderException(Exception):
    """Exception raised for folder-related errors."""
    def __init__(
        self, 
        detail: str = "Folder operation failed",
        status_code: int = 500,
        folder_name: str = None,
        folder_id: str = None
    ):
        self.detail = detail
        self.status_code = status_code
        self.folder_name = folder_name
        self.folder_id = folder_id
        super().__init__(self.detail)


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


class EmailException(HTTPException):
    """
    Exception raised for email-related errors.
    """
    def __init__(self, detail: str = "Email operation failed", folder_name: str = None, message_id: str = None, status_code: int = 500):
        """
        Initialize the exception.

        Args:
            detail (str): A detailed error message
            folder_name (str, optional): The name of the folder involved
            message_id (str, optional): The ID of the message involved
            status_code (int): The HTTP status code (default: 500 Internal Server Error)
        """
        super().__init__(status_code=status_code, detail=detail)
        self.folder_name = folder_name
        self.message_id = message_id


class GraphResponseException(HTTPException):
    """
    Exception raised when Graph API response is invalid or unexpected.

    NOTE: Current use cases:
    - Getting folder collections | MailFolderCollectionResponse
    - Getting message collections | MessageCollectionResponse
    - Getting attachment collections | AttachmentCollectionResponse
    
    - If we don't see these expected types in the response,
     we should raise this exception.

    This will help track changes in the Graph API response format.
    """
    def __init__(
        self, 
        detail: str = "Invalid Graph API response", 
        status_code: int = 500,
        response_type: str = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.response_type = response_type

    def __str__(self):
        base_msg = f"GraphResponseException: {self.detail}"
        if self.response_type:
            base_msg += f" (Expected type: {self.response_type})"
        return base_msg
