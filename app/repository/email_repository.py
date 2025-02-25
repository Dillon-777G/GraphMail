from typing import List, Tuple
import logging

import pymysql
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy import select

from app.persistence.base_connection import get_db

from app.models.persistence_models.email_orm import DBEmail
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException

from app.service.retry_service import RetryService
from app.models.retries.retry_context import RetryContext
from app.models.retries.retry_enums import RetryProfile

from app.utils.constants.repository_constants import RepositoryConstants

"""
SUMMARY:

This repository code logic is incredibly simple. Persist a list of emails. 
What I want to focus on for anyone looking at this class is the flow of 
exceptions to retry logic. 

Basically, the function is called and we chain down into _execute_persist.
If an exception occurs here, we propagate to the retry context. The retry context
then checks whether or not we have an integrity error. If we do, retries are 
aborted. If not it will execute retries. 

Lastly, all exceptions are propagated up to the bulk_save_emails function for 
specific handling.

This was done in order to increase application integrity. The persist call is a 
critical function and we need it to recognize when not to waste processing power.
"""

class EmailRepository:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.retry_service = RetryService(retry_profile=RetryProfile.STANDARD)




    async def bulk_save_emails(self, emails: List[DBEmail]) -> Tuple[List[DBEmail], List[DBEmail], List[DBEmail]]:
        """Bulk save emails to the database."""
        try:
            successful_emails, duplicate_emails, failed_emails = await self._execute_persist(emails)
            
            # Log the results
            if successful_emails:
                self.logger.info("Successfully persisted %d emails", len(successful_emails))
            if duplicate_emails:
                self.logger.info("Found %d duplicate emails", len(duplicate_emails))
            if failed_emails:
                self.logger.warning("Failed to persist %d emails", len(failed_emails))
            
            # Only raise an exception if we have actual failures (not duplicates)
            if failed_emails and not (duplicate_emails or successful_emails):
                raise EmailPersistenceException(
                    f"Failed to persist some emails. {len(failed_emails)} failures."
                )
            
            return successful_emails, duplicate_emails, failed_emails
            
        except Exception as e:
            self.logger.error("Error during bulk email persistence: %s", str(e))
            raise EmailPersistenceException(f"Failed to persist emails: {str(e)}") from e





    async def _persist_emails(self, emails: List[DBEmail]) -> List[DBEmail]:
        """
        Internal method to persist emails to the database.
        Includes retry logic for transient errors.
        """
        retry_context = RetryContext(
            operation=lambda: self._execute_persist(emails),
            error_msg="Failed to persist emails in bulk operation",
            custom_exception=EmailPersistenceException
        )
        
        return await self.retry_service.retry_operation(retry_context)





    async def _execute_persist(self, emails: List[DBEmail]) -> Tuple[List[str], List[str], List[str]]:
        """
        Execute the actual database persist operation.
        Handles each email individually to allow for partial success.
        Returns tuple of (successfully_persisted_ids, duplicate_ids, failed_ids)
        """
        async with get_db() as session:
            successfully_persisted = []
            duplicate_emails = []
            failed_emails = []
            
            for email in emails:
                try:
                    session.add(email)
                    await session.flush()
                    await session.commit()
                    await session.refresh(email)
                    successfully_persisted.append(email)
                except IntegrityError as e:
                    await session.rollback()
                    if isinstance(e.orig, pymysql.err.IntegrityError) and e.orig.args[0] == RepositoryConstants.MYSQL_DUPLICATE_ENTRY_ERROR:
                        self.logger.info("Skipping duplicate email: %s", email)
                        duplicate_emails.append(email)
                    else:
                        self.logger.error("Failed to persist email: %s", email)
                        failed_emails.append(email)
                except Exception:
                    await session.rollback()
                    self.logger.error("Failed with an unknown error, aborting operation. Last email processed: %s", email)
                    raise
            
            return successfully_persisted, duplicate_emails, failed_emails


    async def get_email_id_by_graph_message_id(self, graph_message_id: str) -> int:
        """
        Get the email ID by graph message ID.
        
        Raises:
            NoResultFound: If no email exists with the given graph_message_id
            EmailPersistenceException: If there's a database error
        """
        async with get_db() as session:
            try:
                query = select(DBEmail).where(DBEmail.graph_message_id == graph_message_id)
                result = await session.execute(query)
                email = result.scalar_one()
                return email.id
            except NoResultFound:
                raise 
            except Exception as e:
                raise EmailPersistenceException(
                    detail=f"Unexpected error occurred while getting email ID by graph message ID: {str(e)}",
                    status_code=500
                ) from e