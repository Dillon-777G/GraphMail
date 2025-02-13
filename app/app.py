import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.logging.logging_config import setup_logging
from app.controllers.auth_controller import auth_controller
from app.controllers.attachment_controller import attachment_controller
from app.controllers.folder_controller import folder_controller
from app.controllers.recursive_email_controller import recursive_email_controller
from app.controllers.email_persistence_controller import email_controller
from app.service.graph.graph_authentication_service import Graph
from app.service.graph.graph_id_translation_service import GraphIDTranslator
from app.service.emails.paginated_email_service import PaginatedEmailService
from app.service.emails.download_email_service import EmailDownloadService
from app.service.folder_service import FolderService
from app.service.attachment_service import AttachmentService
from app.service.recursive_email_service import RecursiveEmailService
from app.service.emails.select_email_service import SelectEmailService
from app.repository.email_repository import EmailRepository
from app.error_handling.exceptions.folder_exception import FolderException
from app.error_handling.exceptions.graph_response_exception import GraphResponseException
from app.error_handling.exceptions.recursive_email_exception import RecursiveEmailException
from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException
from app.error_handling.exceptions.email_attachment_exception import EmailAttachmentException
from app.error_handling.exceptions.id_translation_exception import IdTranslationException
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException
from app.error_handling.exception_handler import ExceptionHandler
from app.service.emails.email_cache_service import EmailCacheService


def init_app():
    """ Initializes the FastAPI app and sets up logging. """
    setup_logging()  # Ensures logging is set up before any loggers are created
    logger = logging.getLogger(__name__)

    handler = ExceptionHandler()
    
    app_init = FastAPI(
        exception_handlers={
            AuthenticationFailedException: handler.handle_authentication_error,
            EmailAttachmentException: handler.handle_attachment_error,
            IdTranslationException: handler.handle_id_translation_error,
            FolderException: handler.handle_folder_error,
            GraphResponseException: handler.handle_graph_response_error,
            RecursiveEmailException: handler.handle_recursive_email_error,
            EmailPersistenceException: handler.handle_email_persistence_error,
            Exception: handler.handle_global_error
        }
    )

    # Add CORS middleware
    app_init.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5000",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Initialize shared instances AFTER logging is set up
    graph = Graph()
    graph_translator = GraphIDTranslator(graph)
    email_repository = EmailRepository()
    paginated_email_service = PaginatedEmailService(graph)
    download_email_service = EmailDownloadService(graph, graph_translator)
    folder_service = FolderService(graph)
    attachment_service = AttachmentService(graph)
    email_cache_service = EmailCacheService()
    recursive_email_service = RecursiveEmailService(
        folder_service=folder_service,
        download_email_service=download_email_service,
        email_cache_service=email_cache_service,
        email_repository=email_repository
    )
    select_email_service = SelectEmailService(graph, graph_translator, email_repository, paginated_email_service)

    # Register routes
    app_init.include_router(auth_controller(graph), tags=["auth"])
    app_init.include_router(attachment_controller(graph, attachment_service), prefix="/attachments", tags=["attachment"])
    app_init.include_router(folder_controller(graph, folder_service, paginated_email_service), prefix="/folders", tags=["folders"])
    app_init.include_router(recursive_email_controller(graph, recursive_email_service), prefix="/recursive_emails", tags=["recursive_emails"])
    app_init.include_router(email_controller(graph, select_email_service), prefix="/emails", tags=["emails"])

    logger.info(r"""
                
                
    ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗
    ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║
    ██║  ███╗██████╔╝███████║██████╔╝███████║
    ██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║
    ╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║
    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
                                            
    ███╗   ███╗ █████╗ ██╗██╗                
    ████╗ ████║██╔══██╗██║██║                
    ██╔████╔██║███████║██║██║                
    ██║╚██╔╝██║██╔══██║██║██║                
    ██║ ╚═╝ ██║██║  ██║██║███████╗           
    ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝           
                                            
                """)


    return app_init  # Return the initialized app

# Initialize the app only once, when this module is imported
app = init_app()