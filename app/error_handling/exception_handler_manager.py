from fastapi import Request

from app.error_handling.handlers.authentication_handler import AuthenticationHandler
from app.error_handling.handlers.email_handler import EmailHandler
from app.error_handling.handlers.attachment_handler import AttachmentHandler
from app.error_handling.handlers.id_translation_handler import IdTranslationHandler
from app.error_handling.handlers.folder_handler import FolderHandler
from app.error_handling.handlers.graph_response_handler import GraphResponseHandler
from app.error_handling.handlers.recursive_email_handler import RecursiveEmailHandler
from app.error_handling.handlers.global_handler import GlobalHandler
from app.error_handling.handlers.email_persistence_handler import EmailPersistenceHandler
from app.error_handling.handlers.validation_handler import ValidationHandler
from app.error_handling.handlers.api_not_found_handler import ApiNotFoundHandler
from app.error_handling.handlers.no_result_handler import NoResultHandler
from app.error_handling.handlers.value_error_handler import ValueErrorHandler
from app.error_handling.handlers.client_authentication_handler import ClientAuthenticationHandler
from app.error_handling.handlers.db_email_recipient_handler import DBEmailRecipientHandler

class ExceptionHandlerManager:
    """Coordinates all exception handlers by initializing and delegating to them."""
    
    def __init__(self):
        self.handlers = {
            'auth': AuthenticationHandler(),
            'email': EmailHandler(),
            'attachment': AttachmentHandler(),
            'id_translation': IdTranslationHandler(),
            'folder': FolderHandler(),
            'graph_response': GraphResponseHandler(),
            'recursive_email': RecursiveEmailHandler(),
            'global': GlobalHandler(),
            'email_persistence': EmailPersistenceHandler(),
            'validation': ValidationHandler(),
            'api_not_found': ApiNotFoundHandler(),
            'no_result': NoResultHandler(),
            'value_error': ValueErrorHandler(),
            'client_auth': ClientAuthenticationHandler(),
            'db_email_recipient': DBEmailRecipientHandler(),
        }

    async def handle_authentication_error(self, request: Request, exc):
        return await self.handlers['auth'].handle_authentication_error(request, exc)

    async def handle_email_error(self, request: Request, exc):
        return await self.handlers['email'].handle_email_error(request, exc)

    async def handle_attachment_error(self, request: Request, exc):
        return await self.handlers['attachment'].handle_attachment_error(request, exc)

    async def handle_id_translation_error(self, request: Request, exc):
        return await self.handlers['id_translation'].handle_id_translation_error(request, exc)

    async def handle_folder_error(self, request: Request, exc):
        return await self.handlers['folder'].handle_folder_error(request, exc)

    async def handle_graph_response_error(self, request: Request, exc):
        return await self.handlers['graph_response'].handle_graph_response_error(request, exc)

    async def handle_recursive_email_error(self, request: Request, exc):
        return await self.handlers['recursive_email'].handle_recursive_email_error(request, exc)

    async def handle_global_error(self, request: Request, exc):
        return await self.handlers['global'].handle_global_error(request, exc)

    async def handle_email_persistence_error(self, request: Request, exc):
        return await self.handlers['email_persistence'].handle_email_persistence_error(request, exc)

    async def handle_validation_error(self, request: Request, exc):
        return await self.handlers['validation'].handle_validation_error(request, exc)

    # Api call not found
    async def handle_api_not_found(self, request: Request, exc):
        return await self.handlers['api_not_found'].handle_api_not_found(request, exc)

    # Database query not found
    async def handle_no_result_found(self, request: Request, exc):
        return await self.handlers['no_result'].handle_no_result_found(request, exc)

    async def handle_value_error(self, request: Request, exc):
        return await self.handlers['value_error'].handle_value_error(request, exc)

    async def handle_client_authentication_error(self, request: Request, exc):
        return await self.handlers['client_auth'].handle_client_authentication_error(request, exc)

    async def handle_db_email_recipient_error(self, request: Request, exc):
        return await self.handlers['db_email_recipient'].handle_db_email_recipient_error(request, exc)