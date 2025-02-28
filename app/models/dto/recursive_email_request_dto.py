# Third party imports
from pydantic import (
    BaseModel,
    ConfigDict
)


class RecursiveEmailRequestDTO(BaseModel):
    """
    Request DTO for recursive email operations.
    
    Attributes:
        folder_id (str): The ID of the folder to start the recursive search from
        selection (EmailSelectionDTO): The selection criteria for the emails
        recursive (bool): Whether to recursively search through subfolders
    """
    ref_type: str
    ref_id: int
    created_by: int

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "ref_type": "folder",
                "ref_id": 1234567890,
                "created_by": 1234567890
            }
        }
    )
