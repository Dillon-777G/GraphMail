from typing import List
import logging

import pymysql
from sqlalchemy.exc import IntegrityError
from app.persistence.base_connection import get_db

from app.models.persistence_models.email_orm import DBEmail
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException

from app.utils.retry_utils import RetryUtils
from app.models.retries.retry_context import RetryContext
from app.models.retries.retry_enums import RetryProfile



"""
SUMMARY:

This repository code logic is incredibly simple. Persist a list of emails. 
What I want to focus on for anyone looking at this class is the flow of 
exceptions to retry logic. 

Basically, the function is called and we chain down into _execute_persist.
If an exception occurs here, we propagate to the retry context. The retry context
then checks whether or not we have an integrity error. If we do, retries are 
aborted. If not it will execute retries. 

Lastly, all exceptions are propagated up to the bulk_create_emails function for 
specific handling.

This was done in order to increase application integrity. The persist call is a 
critical function and we need it to recognize when not to waste processing power.
"""
MYSQL_DUPLICATE_ENTRY_ERROR = 1062

class EmailRepository:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.retry_utils = RetryUtils(retry_profile=RetryProfile.BATCH)




    async def bulk_create_emails(self, emails: List[DBEmail]) -> List[DBEmail]:
        """
        Bulk create emails in the database with retry logic and error handling.
        
        Args:
            emails (List[DBEmail]): List of email objects to persist
            
        Returns:
            List[DBEmail]: List of persisted email objects with IDs
            
        Raises:
            EmailPersistenceException: If database operation fails
        """
        if not emails:
            return []

        try:
            return await self._persist_emails(emails)
        except IntegrityError as e:
            # Handle MySQL duplicate key error specifically
            if isinstance(e.orig, pymysql.err.IntegrityError) and e.orig.args[0] == MYSQL_DUPLICATE_ENTRY_ERROR:
                raise EmailPersistenceException(
                    detail="Duplicate email detected in the database",
                    status_code=409,
                    message_ids=[email.graph_source_id for email in emails]
                ) from e
            # Other integrity errors
            raise EmailPersistenceException(
                detail="Database constraint violation",
                status_code=500,
                message_ids=[email.graph_source_id for email in emails]
            ) from e
        except Exception as e:
            raise EmailPersistenceException(
                detail=f"Failed to persist emails: {str(e)}",
                status_code=500,
                message_ids=[email.graph_source_id for email in emails]
            ) from e





    async def _persist_emails(self, emails: List[DBEmail]) -> List[DBEmail]:
        """
        Internal method to persist emails to the database.
        Includes retry logic for transient errors.
        """
        retry_context = RetryContext(
            operation=lambda: self._execute_persist(emails),
            error_msg="Failed to persist emails in bulk operation",
            custom_exception=EmailPersistenceException,
            abort_on_exceptions=[IntegrityError]  # Immediately abort on integrity errors
        )
        
        return await self.retry_utils.retry_operation(retry_context)





    async def _execute_persist(self, emails: List[DBEmail]) -> List[DBEmail]:
        """
        Execute the actual database persist operation.
        """
        async with get_db() as session:
            try:
                session.add_all(emails)
                await session.flush()
                await session.commit()
                
                for email in emails:
                    await session.refresh(email)
                
                return emails
                
            except Exception: # we don't need to be granular here, we are passing up to specific handling later 
                await session.rollback()
                raise 