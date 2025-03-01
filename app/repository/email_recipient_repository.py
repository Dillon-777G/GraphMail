# Python standard library imports
import logging
from typing import List

# Application imports
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException
from app.models.persistence_models.email_recipient_orm import DBEmailRecipient
from app.models.retries.retry_context import RetryContext
from app.persistence.base_connection import get_db
from app.service.retry_service import RetryProfile, RetryService


class EmailRecipientRepository:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.retry_service = RetryService(retry_profile=RetryProfile.STANDARD)

    async def bulk_save_recipients(self, recipients: List[DBEmailRecipient]):
        """
        Bulk save email recipients
        """
        retry_context = RetryContext(
            operation=lambda: self._execute_persist(recipients),
            error_msg="Failed to persist recipients in bulk operation",
        )
        return await self.retry_service.retry_operation(retry_context)

    async def _execute_persist(self, recipients: List[DBEmailRecipient]):
        """
        Internal method to persist recipients to the database.
        Includes retry logic for transient errors.
        """
        async with get_db() as session:

            self.logger.info("Starting to persist %d recipients", len(recipients))
            for recipient in recipients:
                try:
                    session.add(recipient)
                    await session.flush([recipient])
                    await session.commit()
                    
                except Exception as e:
                    await session.rollback()
                    self.logger.error("Failed to save recipient: %s", str(e))
                    raise EmailPersistenceException(f"Failed to save recipient: {str(e)}") from e
            
            self.logger.info("Successfully persisted %d recipients", len(recipients))
