import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

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
from app.service.attachments.attachment_graph_service import AttachmentGraphService
from app.service.emails.recursive_email_service import RecursiveEmailService
from app.service.emails.select_email_service import SelectEmailService
from app.service.emails.email_cache_service import EmailCacheService
from app.service.attachments.attachment_file_service import AttachmentFileService
from app.service.session_store.session_store_service import SessionStore

from app.service.emails.email_crud_service import EmailCRUDService
from app.service.attachments.attachment_crud_service import AttachmentCRUDService

from app.repository.email_repository import EmailRepository
from app.repository.attachment_repository import AttachmentRepository

from app.error_handling.exception_config import get_exception_handlers
from app.error_handling.exception_handler_manager import ExceptionHandlerManager

from app.config.environment_config import EnvironmentConfig

from app.persistence.base_connection import init_db



@asynccontextmanager
async def lifespan(_: FastAPI): #we need the type hinting here but we aren't using the application object
    """Manages the lifecycle of the FastAPI application.
    
    This context manager handles database initialization during startup and cleanup during shutdown.
    It ensures proper database connection management throughout the application's lifecycle.
    
    Args:
        application (FastAPI): The FastAPI application instance.
        
    Yields:
        None: Control is yielded back to FastAPI to run the application.
        
    Raises:
        SQLAlchemyError: If database initialization or cleanup fails.
        ConnectionError: If database connection cannot be established or closed.
    """
    logger = logging.getLogger(__name__)
    try:
        # Initialize the DB session maker and store it in the app state.
        engine, session_maker = init_db()
        logger.info("DB session maker initialized.")
        
        # Test query to verify the connection.
        async with session_maker() as session:
            result = await session.execute(text('SHOW TABLES'))
            logger.info("Database test query returned: %s", result.scalar())
            
        logger.info("Lifespan startup complete. Database connection test succeeded.")
    except Exception as e:
        logger.exception("Database initialization failed: %s", e)
        raise

    yield  # Application runs here.

    # Cleanup database connections
    try:
        if engine:
            # Close the session maker engine
            await engine.dispose()
            logger.info("Database connections cleaned up successfully.")
    except (SQLAlchemyError, ConnectionError) as e:
        logger.exception("Error during database cleanup: %s", e)

    logger.info("Shutting down...Goodbye!")




def init_app() -> FastAPI:
    """Initializes the FastAPI app and sets up all shared resources."""
    setup_logging()
    EnvironmentConfig.load_environment()
    handler = ExceptionHandlerManager()
    app_init = FastAPI(
        lifespan=lifespan,
        exception_handlers=get_exception_handlers(handler)
    )
    logger = logging.getLogger(__name__)

    # Add CORS middleware
    app_init.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5000", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Initialize core services
    graph = Graph()
    graph_translator = GraphIDTranslator(graph)
    
    # Initialize repositories
    repositories = {
        'email': EmailRepository(),
        'attachment': AttachmentRepository()
    }

    # Initialize services
    services = create_services(graph, graph_translator, repositories)

    # Register routes
    register_routes(app_init, graph, services)

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
    return app_init


def create_services(graph, graph_translator, repositories):
    """Creates and returns a dictionary of service instances."""
    email_crud = EmailCRUDService(repositories['email'])
    attachment_crud = AttachmentCRUDService(repositories['attachment'])
    
    return {
        'paginated_email': PaginatedEmailService(graph),
        'download_email': EmailDownloadService(graph, graph_translator),
        'folder': FolderService(graph),
        'attachment_graph': AttachmentGraphService(
            graph, email_crud, attachment_crud, AttachmentFileService()
        ),
        'email_cache': EmailCacheService(),
        'recursive_email': RecursiveEmailService(
            folder_service=FolderService(graph),
            download_email_service=EmailDownloadService(graph, graph_translator),
            email_cache_service=EmailCacheService(),
            email_repository=repositories['email']
        ),
        'select_email': SelectEmailService(
            graph, graph_translator, repositories['email'], PaginatedEmailService(graph)
        ),
        'session_store': SessionStore()
    }




def register_routes(app_for_routes, graph, services):
    """Registers all route handlers with the FastAPI application."""
    app_for_routes.include_router(auth_controller(graph, services['session_store']), tags=["auth"])
    app_for_routes.include_router(
        attachment_controller(graph, services['attachment_graph']), 
        prefix="/attachments", 
        tags=["attachment"]
    )
    app_for_routes.include_router(
        folder_controller(graph, services['folder'], services['paginated_email'], services['session_store']), 
        prefix="/folders", 
        tags=["folders"]
    )
    app_for_routes.include_router(
        recursive_email_controller(graph, services['recursive_email']), 
        prefix="/recursive_emails", 
        tags=["recursive_emails"]
    )
    app_for_routes.include_router(
        email_controller(graph, services['select_email']), 
        prefix="/emails", 
        tags=["emails"]
    )

# Initialize the app only once, when this module is imported
app = init_app()