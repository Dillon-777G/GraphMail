from fastapi import HTTPException

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