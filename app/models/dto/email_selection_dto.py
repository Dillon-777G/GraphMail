from typing import List
from pydantic import BaseModel, Field

class EmailSelectionDTO(BaseModel):
    """
    Data Transfer Object for email selection request parameters.
    
    Attributes:
        source_ids (List[str]): List of Graph API source IDs to fetch
        ref_id (int): Reference ID for the emails (e.g., matter ID, case ID)
        ref_type (str): Type of reference (e.g., "MATTER", "CASE")
        created_by (int): User ID of the person making the request
    """
    
    email_source_ids: List[str] = Field(..., min_items=1, max_items=50)
    ref_id: int = Field(..., gt=0)
    ref_type: str = Field(..., min_length=1, max_length=30)
    created_by: int = Field(..., gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "email_source_ids": ["AAMkAGVmMDEzMTM4LTZmYWUtNDdkNC1hMDZa..."],
                "ref_id": 12345,
                "ref_type": "MATTER",
                "created_by": 67890
            }
        } 