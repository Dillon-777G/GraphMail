class FolderException(Exception):
    """Exception raised for folder-related errors."""
    
    def __init__(
        self, 
        detail: str = "Folder operation failed",
        status_code: int = 500,
        folder_name: str = None,
        folder_id: str = None
    ):
        self.detail = detail
        self.status_code = status_code
        self.folder_name = folder_name
        self.folder_id = folder_id
        super().__init__(self.detail) 