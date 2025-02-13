import logging
from datetime import datetime

from app.models.dto.email_selection_dto import EmailSelectionDTO
from app.models.email import Email
from app.models.persistence_models.email_orm import DBEmail
from app.error_handling.exceptions.db_email_exception import DBEmailException
from app.models.dto.recursive_email_request_dto import RecursiveEmailRequestDTO
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
                to_addr="; ".join(email.receivers),
                subject=email.subject or "No Subject",
                body=email.body or "",
                email_date=email.received_date,
                created_by=selection.created_by,
                created_date=datetime.utcnow(),
                rmc_include=False,
                vendor_include=False,
                cc_addr="; ".join(email.cc) if email.cc else None,
                bcc_addr="; ".join(email.bcc) if email.bcc else None,
                graph_message_id=immutable_id,
                graph_source_id=email.source_id,
                graph_conversation_id=email.conversation_id,
                is_read=email.is_read,
                has_attachments=email.has_attachments
            )
        except (TypeError, ValueError) as e:
            logger.error("Validation error when creating the DBEmail model: %s", e)
            raise DBEmailException("Failed to create DBEmail due to a valiation error", immutable_id, email.source_id) from e



    @staticmethod
    def email_to_db_email_recursive(
        email: Email,
        selection: RecursiveEmailRequestDTO) -> DBEmail:
        """
        Convert Email model to DBEmail model for the recursive email service.
        
        Args:
            email: Email model instance
            
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
                to_addr="; ".join(email.receivers),
                subject=email.subject or "No Subject",
                body=email.body or "",
                email_date=email.received_date,
                created_by=selection.created_by,
                created_date=datetime.utcnow(),
                rmc_include=False,
                vendor_include=False,
                cc_addr="; ".join(email.cc) if email.cc else None,
                bcc_addr="; ".join(email.bcc) if email.bcc else None,
                graph_message_id=email.message_id,
                graph_source_id=email.source_id,
                graph_conversation_id=email.conversation_id,
                is_read=email.is_read,
                has_attachments=email.has_attachments
            )
        except (TypeError, ValueError) as e:
            logger.error("Validation error when creating the DBEmail model: %s", e)
            raise DBEmailException("Failed to create DBEmail due to a valiation error", email.message_id, email.source_id) from e
