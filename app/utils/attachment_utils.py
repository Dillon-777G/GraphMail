# Python standard library imports
import logging

# Application imports
from app.models.email_attachment import EmailAttachment
from app.models.persistence_models.attachment_orm import DBAttachment

logger = logging.getLogger(__name__)

class AttachmentUtils:
    @staticmethod
    def attachment_to_db_attachment(attachment: EmailAttachment, email_id: int) -> DBAttachment:
        logger.info("Converting attachment to DBAttachment: %s", attachment.name)
        db_attachment = DBAttachment(
            email_id=email_id,
            name=attachment.name,
            graph_attachment_id=attachment.id,
        )
        db_attachment.generate_unique_url()
        logger.info("Generated URL: %s", db_attachment.url)
        return db_attachment