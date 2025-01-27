# Standard library imports
import logging

# Third party imports
from fastapi import FastAPI

# Local application imports
from app.logging.logging_config import setup_logging
from app.controllers.auth_controller import auth_controller
from app.controllers.email_controller import email_controller
from app.controllers.attachment_controller import attachment_controller
from app.controllers.folder_controller import folder_controller
from app.service.graph_service import Graph
from app.service.email_service import EmailService
from app.service.folder_service import FolderService
from app.service.attachment_service import AttachmentService
from app.utils.graph_utils import GraphUtils

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Graph Email API",
    description="API for interacting with Microsoft Graph Email"
)

# Initialize shared Graph instance
graph = Graph()
graph_utils = GraphUtils(graph)
email_service = EmailService(graph_utils)
folder_service = FolderService(graph_utils)
attachment_service = AttachmentService(graph_utils)

# Include routers with shorter lines
app.include_router(
    auth_controller(graph),
    tags=["auth"]
)
app.include_router(
    email_controller(graph, email_service),
    prefix="/graph",
    tags=["emails"]
)
app.include_router(
    attachment_controller(graph, attachment_service),
    prefix="/attachments",
    tags=["attachment"]
)
app.include_router(
    folder_controller(graph, folder_service, email_service),
    prefix="/folders",
    tags=["folders"]
)

logger.info(r"""
 ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗
██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║
██║  ███╗██████╔╝███████║██████╔╝███████║
██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║
╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
                                         
██████╗ ███████╗███╗   ███╗ ██████╗      
██╔══██╗██╔════╝████╗ ████║██╔═══██╗     
██║  ██║█████╗  ██╔████╔██║██║   ██║     
██║  ██║██╔══╝  ██║╚██╔╝██║██║   ██║     
██████╔╝███████╗██║ ╚═╝ ██║╚██████╔╝     
╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝          
    
            """)
