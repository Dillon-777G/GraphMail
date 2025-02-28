# Third party imports
from azure.core.exceptions import ClientAuthenticationError
from fastapi.exceptions import RequestValidationError
from kiota_abstractions.api_error import APIError
from sqlalchemy.exc import NoResultFound

# Local imports
from app.error_handling.exception_handler_manager import ExceptionHandlerManager
from app.error_handling.exceptions.attachment_persistence_exception import AttachmentPersistenceException
from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException
from app.error_handling.exceptions.db_email_recipient_exception import DBEmailRecipientException
from app.error_handling.exceptions.email_attachment_exception import EmailAttachmentException
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException
from app.error_handling.exceptions.folder_exception import FolderException
from app.error_handling.exceptions.graph_response_exception import GraphResponseException
from app.error_handling.exceptions.id_translation_exception import IdTranslationException
from app.error_handling.exceptions.recursive_email_exception import RecursiveEmailException


def get_exception_handlers(handler: ExceptionHandlerManager) -> dict:
    """
    Returns a mapping of exceptions to their handlers.
    Centralizes exception handling configuration.
    """
    return {
        404: handler.handle_api_not_found,
        APIError: handler.handle_api_error,
        AttachmentPersistenceException: handler.handle_attachment_persistence_error,
        AuthenticationFailedException: handler.handle_authentication_error,
        ClientAuthenticationError: handler.handle_client_authentication_error,
        DBEmailRecipientException: handler.handle_db_email_recipient_error,
        EmailAttachmentException: handler.handle_attachment_error,
        EmailPersistenceException: handler.handle_email_persistence_error,
        FolderException: handler.handle_folder_error,
        GraphResponseException: handler.handle_graph_response_error,
        IdTranslationException: handler.handle_id_translation_error,
        NoResultFound: handler.handle_no_result_found,
        RecursiveEmailException: handler.handle_recursive_email_error,
        RequestValidationError: handler.handle_validation_error,
        ValueError: handler.handle_value_error,

        #exception to the alphabetical order so it can be easily tested
        Exception: handler.handle_global_error,
    } 