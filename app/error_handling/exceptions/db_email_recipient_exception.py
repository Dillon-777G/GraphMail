from typing import Optional, List
from fastapi import HTTPException

class DBEmailRecipientException(HTTPException):
    """
    Raised when there are failures related to email recipient operations.
    Primarily concerned with recipient persistence operations.

    Args:
        detail (str): A detailed error message
        email_id (int, optional): The ID of the email associated with the recipients
        recipient_addresses (List[str], optional): List of recipient email addresses that failed
        status_code (int): The HTTP status code (default: 500 Internal Server Error)
    """

    def __init__(
        self, 
        detail: str = "Email recipient operation has failed", 
        email_id: Optional[int] = None, 
        recipient_addresses: Optional[List[str]] = None,
        status_code: int = 500
    ):
        self.detail = detail
        self.email_id = email_id
        self.recipient_addresses = recipient_addresses or []
        self.status_code = status_code
        super().__init__(status_code=status_code, detail=detail)
    
    def __str__(self) -> str:
        base_msg = f"DBEmailRecipientException: {self.detail}"
        if self.email_id:
            base_msg += f" (Email ID: {self.email_id})"
        if self.recipient_addresses:
            addresses_str = ", ".join(self.recipient_addresses[:5])
            if len(self.recipient_addresses) > 5:
                addresses_str += f"... and {len(self.recipient_addresses) - 5} more"
            base_msg += f" (Recipients: {addresses_str})"
        return base_msg 