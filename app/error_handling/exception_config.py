from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import NoResultFound
from azure.core.exceptions import ClientAuthenticationError

from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException
from app.error_handling.exceptions.email_attachment_exception import EmailAttachmentException
from app.error_handling.exceptions.id_translation_exception import IdTranslationException
from app.error_handling.exceptions.folder_exception import FolderException
from app.error_handling.exceptions.graph_response_exception import GraphResponseException
from app.error_handling.exceptions.recursive_email_exception import RecursiveEmailException
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException
from app.error_handling.exception_handler_manager import ExceptionHandlerManager
from app.error_handling.exceptions.db_email_recipient_exception import DBEmailRecipientException

def get_exception_handlers(handler: ExceptionHandlerManager) -> dict:
    """
    Returns a mapping of exceptions to their handlers.
    Centralizes exception handling configuration.
    """
    return {
        404: handler.handle_not_found,
        RequestValidationError: handler.handle_validation_error,
        AuthenticationFailedException: handler.handle_authentication_error,
        EmailAttachmentException: handler.handle_attachment_error,
        IdTranslationException: handler.handle_id_translation_error,
        FolderException: handler.handle_folder_error,
        GraphResponseException: handler.handle_graph_response_error,
        RecursiveEmailException: handler.handle_recursive_email_error,
        EmailPersistenceException: handler.handle_email_persistence_error,
        NoResultFound: handler.handle_no_result_found,
        Exception: handler.handle_global_error,
        ValueError: handler.handle_value_error,
        ClientAuthenticationError: handler.handle_client_authentication_error,
        DBEmailRecipientException: handler.handle_db_email_recipient_error,
    } 