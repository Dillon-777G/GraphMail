# Python standard library imports
import logging

# Third party imports
import pymysql
from sqlalchemy.exc import IntegrityError

# Application imports
# Error handling
from app.error_handling.exceptions.attachment_persistence_exception import AttachmentPersistenceException

# Models
from app.models.persistence_models.attachment_orm import DBAttachment
from app.models.retries.retry_context import RetryContext
from app.models.retries.retry_enums import RetryProfile

# Persistence
from app.persistence.base_connection import get_db

# Services
from app.service.retry_service import RetryService

# Utils
from app.utils.constants.repository_constants import RepositoryConstants


class AttachmentRepository:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.retry_service = RetryService(retry_profile=RetryProfile.STANDARD)

    
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
        self.logger.info("Attemping to persist attachment: %s", attachment.graph_attachment_id)
        retry_context = RetryContext(
            operation=lambda: self._persist_attachment(attachment),
            error_msg="Failed to persist attachment",
            abort_on_exceptions=[AttachmentPersistenceException]
        )
        
        return await self.retry_service.retry_operation(retry_context)
        


    async def _persist_attachment(self, attachment: DBAttachment) -> DBAttachment:
        """
        Internal method to persist an attachment to the database.
        """
        async with get_db() as session:
            try:
                session.add(attachment)
                await session.flush()
                await session.commit()
                await session.refresh(attachment)
                self.logger.info("Attachment persisted successfully: %s", attachment.graph_attachment_id)
                return attachment
            except IntegrityError as e:
                if isinstance(e.orig, pymysql.err.IntegrityError) and e.orig.args[0] == RepositoryConstants.MYSQL_DUPLICATE_ENTRY_ERROR:
                    self.logger.error("Duplicate attachment detected in the database: %s", attachment.graph_attachment_id)
                    raise AttachmentPersistenceException(
                        detail="Duplicate attachment detected in the database",
                        status_code=409,
                        attachment=attachment
                    ) from e
                self.logger.error("Database constraint violation: %s", attachment.graph_attachment_id)
                raise AttachmentPersistenceException(
                    detail="Database constraint violation",
                    status_code=500,
                    attachment=attachment
                ) from e
            except Exception as e:  
                self.logger.error("Failed to persist attachment: %s", attachment.graph_attachment_id)
                raise AttachmentPersistenceException(
                    detail=f"Failed to persist attachment: {str(e)}",
                    status_code=500,
                    attachment=attachment
                ) from e






