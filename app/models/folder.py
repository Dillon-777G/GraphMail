# Standard library imports
from typing import Optional

# Third party imports
from pydantic import BaseModel

"""
FOLDER MODEL:

This model represents a mail folder in the email system.
It maps to the Microsoft Graph mailFolder resource type.
This model is being used to create functionality to navigate
through email folders and select a folder to read emails from.

NOTE: Ids are UNIQUE, no need to translate to immutable ids.

LINK: https://learn.microsoft.com/en-us/graph/api/resources/mailfolder?view=graph-rest-1.0
"""

class Folder(BaseModel):
    """
    Represents a mail folder in the email system.
    Maps to Microsoft Graph mailFolder resource type.

    Attributes:
        id (str): The folder's unique identifier.
        display_name (str): The folder's display name.
        parent_folder_id (Optional[str]): The unique identifier for the parent folder.
        child_folder_count (int): Number of immediate child folders.
        total_item_count (int): Number of items in the folder.
        unread_item_count (int): Number of unread items in the folder.
        is_hidden (bool): Indicates whether the folder is hidden.
    """
    id: str
    display_name: str
    parent_folder_id: Optional[str]
    child_folder_count: int
    total_item_count: int
    unread_item_count: int
    is_hidden: bool

    @classmethod
    def from_graph_folder(cls, folder):
        """
        Create a Folder instance from a Microsoft Graph mailFolder object.

        Args:
            folder: Microsoft Graph mailFolder object.

        Returns:
            Folder: New instance with mapped properties.
        """
        return cls(
            id=folder.id,
            display_name=folder.display_name or "Unnamed Folder",
            parent_folder_id=getattr(folder, 'parent_folder_id', None),
            child_folder_count=getattr(folder, 'child_folder_count', 0),
            total_item_count=getattr(folder, 'total_item_count', 0),
            unread_item_count=getattr(folder, 'unread_item_count', 0),
            is_hidden=getattr(folder, 'is_hidden', False)
        )