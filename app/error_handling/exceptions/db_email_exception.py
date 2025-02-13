from typing import Optional
from fastapi import HTTPException

class DBEmailException(HTTPException):
    """
    Raised when the db exception class experiences failures. 
    Its main concern is the persistence APIs

    Args:
        detail (str): A detailed error message
        message_id (str, optional): The ID of the message involved, can be null if translating failed
        source_id (str, optional): Id of the message in the original graph response
        status_code (int): The HTTP status code (default: 500 Internal Server Error)
    """

    def __init__(
        self, 
        detail: str = "Db email operation has failed", 
        message_id: Optional[str] = None, 
        source_id: Optional[str] = None, 
        status_code: int = 500
    ):
        self.detail = detail
        self.message_id = message_id
        self.source_id = source_id
        self.status_code = status_code
        super().__init__(status_code=status_code, detail=detail)
