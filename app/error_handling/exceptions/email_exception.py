from fastapi import HTTPException

class EmailException(HTTPException):
    """Exception raised for email-related errors."""
    
    def __init__(self, detail: str = "Email operation failed", folder_id: str = None, message_id: str = None, status_code: int = 500):
        """
        Initialize the exception.

        Args:
            detail (str): A detailed error message
            folder_id (str, optional): The id of the folder involved
            message_id (str, optional): The ID of the message involved
            status_code (int): The HTTP status code (default: 500 Internal Server Error)
        """
        super().__init__(status_code=status_code, detail=detail)
        self.folder_id = folder_id
        self.message_id = message_id 