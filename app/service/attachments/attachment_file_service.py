import os
import logging

from app.models.persistence_models.attachment_orm import DBAttachment
from app.error_handling.exceptions.attachment_persistence_exception import AttachmentPersistenceException

class AttachmentFileService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def save_attachment_file(self, attachment: DBAttachment, content: bytes) -> None:
        """
        Save attachment content to the file system.

        Args:
            attachment (DBAttachment): The attachment metadata
            content (bytes): The binary content of the attachment

        Raises:
            AttachmentPersistenceException: If the file cannot be saved
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(attachment.url), exist_ok=True)
            
            # Write the file
            with open(attachment.url, 'wb') as file:
                file.write(content)

            os.chmod(attachment.url, 0o664)
                
            self.logger.info("Successfully saved attachment file: %s", attachment.url)
            
        except Exception as e:
            self.logger.error("Failed to save attachment file: %s", str(e))
            raise AttachmentPersistenceException(
                detail=f"Failed to save attachment file: {str(e)}",
                status_code=500,
                attachment=attachment
            ) from e 