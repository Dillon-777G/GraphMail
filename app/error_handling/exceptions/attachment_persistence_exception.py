# Third party imports
from fastapi import HTTPException

# App imports
from app.models.persistence_models.attachment_orm import DBAttachment

class AttachmentPersistenceException(HTTPException):
    """Exception raised for errors during attachment persistence operations."""
    def __init__(self, 
                detail: str = None,
                attachment: DBAttachment = None,
                status_code: int = 500,
                original_error: Exception = None):
        super().__init__(status_code=status_code, detail=detail)
        self.attachment = attachment
        self.original_error = original_error