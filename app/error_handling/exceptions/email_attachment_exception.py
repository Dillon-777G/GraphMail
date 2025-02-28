# Third party imports
from fastapi import HTTPException

class EmailAttachmentException(HTTPException):
    """Exception raised for invalid or unsupported attachments."""
    
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