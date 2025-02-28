# Python standard library imports
import logging

# Application imports
from app.repository.attachment_repository import AttachmentRepository
from app.models.persistence_models.attachment_orm import DBAttachment

logger = logging.getLogger(__name__)

class AttachmentCRUDService:
    def __init__(self, attachment_repository: AttachmentRepository):
        self.attachment_repository = attachment_repository
        self.logger = logging.getLogger(__name__)

    async def save_attachment(self, attachment: DBAttachment) -> DBAttachment:
        """
        Save an attachment to the database.

        Args:
            attachment (DBAttachment): The attachment to save.

        Returns:
            DBAttachment: The saved attachment.

        Raises:
            AttachmentPersistenceException: If the attachment cannot be saved.          
        """
        self.logger.info("Attempting to persist attachment: %s", attachment.graph_attachment_id)
        return await self.attachment_repository.save_attachment(attachment)
