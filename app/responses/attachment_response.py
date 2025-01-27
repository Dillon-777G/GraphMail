import json
from typing import Dict, Any
from fastapi.responses import Response

class AttachmentDownloadResponse(Response):
    """
    Response class so that if a user downloads an attachment, the system can read the metadata from the header
    and then use it to persist the attachment data to the database.

    NOTE: to ensure uniqueness of the attachment, 
    """
    def __init__(self, file_content: bytes, content_type: str, filename: str, metadata: Dict[str, Any]):
        # Convert metadata to a compact JSON string
        metadata_json = json.dumps(metadata, separators=(',', ':'))
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Attachment-Metadata": metadata_json
        }
        super().__init__(content=file_content, media_type=content_type, headers=headers)