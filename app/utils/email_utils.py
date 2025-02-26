import logging
from datetime import datetime
from typing import List


from app.models.dto.email_selection_dto import EmailSelectionDTO
from app.models.email import Email
from app.models.persistence_models.email_orm import DBEmail
from app.models.persistence_models.email_recipient_orm import DBEmailRecipient
from app.models.persistence_models.email_recipient_types import RecipientType

from app.error_handling.exceptions.db_email_exception import DBEmailException
from app.error_handling.exceptions.db_email_recipient_exception import DBEmailRecipientException

logger = logging.getLogger(__name__)

class EmailUtils:  

    @staticmethod
    def email_to_db_email(
        email: Email, 
        selection: EmailSelectionDTO,
        immutable_id: str) -> DBEmail:
        """
        Convert Email model to DBEmail model.
        
        Args:
            email: Email model instance
            selection: Selection parameters including reference info
            immutable_id: Translated immutable ID
            
        Returns:
            DBEmail: Converted database email object

        Raises:
            DBEmailException if there are any issues converting
        """
        try:
            return DBEmail(
                ref_id=selection.ref_id,
                ref_type=selection.ref_type,
                from_addr=email.sender,
                subject=email.subject or "No Subject",
                body=email.body or "",
                email_date=email.received_date,
                created_by=selection.created_by,
                created_date=datetime.utcnow(),
                graph_message_id=immutable_id,
                graph_source_id=email.source_id,
                graph_conversation_id=email.conversation_id,
                is_read=email.is_read,
                has_attachments=email.has_attachments
            )
        except (TypeError, ValueError) as e:
            logger.error("Validation error when creating the DBEmail model: %s", e)
            raise DBEmailException("Failed to create DBEmail due to a validation error", immutable_id, email.source_id) from e



    @staticmethod
    def email_to_db_email_recursive(email: Email, request) -> DBEmail:
        """
        Convert an Email model to a DBEmail model for recursive email processing.
        
        Args:
            email (Email): The email object to convert
            request (RecursiveEmailRequestDTO): The request containing reference information
        """
        try:
            return DBEmail(
            ref_id=request.ref_id,
            ref_type=request.ref_type,
            from_addr=email.sender,
            subject=email.subject,
            body=email.body,
            email_date=email.received_date,
            created_by=request.created_by,
            graph_message_id=email.source_id,
            graph_source_id=email.source_id,
            graph_conversation_id=email.conversation_id,
            is_read=email.is_read,
            has_attachments=email.has_attachments
            )
        except (TypeError, ValueError) as e:
            logger.error("Validation error when creating the DBEmail model: %s", e)
            raise DBEmailException("Failed to create DBEmail due to a validation error", email.source_id, email.source_id) from e


    @staticmethod
    def extract_recipients_from_email(email: Email, email_id: int) -> List[DBEmailRecipient]:
        """
        Extract recipients from an email and return them as a list of DBEmailRecipient objects.
        
        Args:
            email (Email): The email object containing recipient information
            email_id (int): The ID of the email in the database
            
        Returns:
            List[DBEmailRecipient]: A list of DBEmailRecipient objects containing recipient information
        """
        try:
            recipients = []
            
            # TO recipients
            if email.receivers:
                recipients.extend([
                    DBEmailRecipient(
                        email_id=email_id,
                        email_address=addr,
                        recipient_type=RecipientType.TO
                    ) for addr in email.receivers
                ])

            # CC recipients
            if email.cc:
                recipients.extend([
                    DBEmailRecipient(
                        email_id=email_id,
                        email_address=addr,
                        recipient_type=RecipientType.CC
                    ) for addr in email.cc
                ])

            # BCC recipients
            if email.bcc:
                recipients.extend([
                    DBEmailRecipient(
                        email_id=email_id,
                        email_address=addr,
                        recipient_type=RecipientType.BCC
                    ) for addr in email.bcc
                ])

            return recipients
        except (TypeError, ValueError) as e:
            logger.error("Validation error when extracting recipients from email: %s", e)
            raise DBEmailRecipientException("Failed to extract recipients from email due to a validation error", email.source_id) from e


    @staticmethod
    def extract_recipients_from_init_response_emails(init_response_emails: List[Email], successful_emails: List[DBEmail]) -> List[DBEmailRecipient]:
        """
        Extract recipients from a list of emails and match them with their corresponding database records.
        
        Args:
            init_response_emails (List[Email]): List of Email objects from the initial API response
            successful_emails (List[DBEmail]): List of successfully persisted DBEmail records
            
        Returns:
            List[DBEmailRecipient]: List of DBEmailRecipient objects containing recipient information
            
        This function:
        1. Creates a mapping of graph_source_id to DBEmail records
        2. Matches each init_response_email with its corresponding DB record using source_id
        3. Extracts recipients (TO, CC, BCC) from each matched email
        4. Returns a combined list of all recipients as DBEmailRecipient objects
        """
        logger.info("Extracting recipients from initial graph response email objects")
        db_email_map = {db_email.graph_source_id: db_email for db_email in successful_emails}

        all_recipients = []
        for init_response_email in init_response_emails:
            if init_response_email.source_id in db_email_map:
                db_email = db_email_map[init_response_email.source_id]
                recipients = EmailUtils.extract_recipients_from_email(init_response_email, db_email.email_id)
                all_recipients.extend(recipients)

        return all_recipients

    @staticmethod
    def extract_email_ids_from_results(successful_emails, duplicate_emails, failed_emails):
        """
        Extract email IDs from database operation results. Using the graph message id for
        duplicates and failures. to avoid a fetch call on our database.
        
        Args:
            successful_emails: List of successfully saved email objects
            duplicate_emails: List of emails that were duplicates
            failed_emails: List of emails that failed to save
            
        Returns:
            Tuple containing:
            - List of successful email IDs
            - List of duplicate  graph message ids
            - List of failed graph source ids
        """
        logger.info("Extracting successful, duplicate and failed email ids from results")
        successful_email_ids = [email.email_id for email in successful_emails]
        duplicate_email_ids = [email.graph_message_id for email in duplicate_emails]
        failed_email_ids = [email.graph_source_id for email in failed_emails]
        return successful_email_ids, duplicate_email_ids, failed_email_ids
