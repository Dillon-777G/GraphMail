from fastapi import HTTPException

class AuthenticationFailedException(HTTPException):
    """Exception raised for authentication-related issues during token exchange."""
    
    def __init__(self, detail: str = "Authentication failed", status_code: int = 401):
        """
        Initialize the exception.

        Args:
            detail (str): A detailed error message.
            status_code (int): The HTTP status code (default: 401 Unauthorized).
        """
        super().__init__(status_code=status_code, detail=detail) 