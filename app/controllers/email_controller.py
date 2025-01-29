import logging
from typing import Union

from fastapi import APIRouter, Depends
from starlette.responses import RedirectResponse

from app.service.email_service import EmailService
from app.service.graph_service import Graph
from app.fAPI_dependencies.auth_dependency import AuthDependency

logger = logging.getLogger(__name__)

def email_controller(graph: Graph, email_service: EmailService) -> APIRouter:
    router = APIRouter()
    auth = AuthDependency(graph)
    
    @router.get("/emails")
    async def get_emails(folder_name: str,
     auth_response: Union[RedirectResponse, None] = Depends(auth)):
        """
        Fetch emails from a specified folder.
        """
        if auth_response:
            return auth_response
        
        emails = await email_service.get_folder_emails(folder_name)
        return {
            "status": "success",
            "data": [
                {
                    "message_id": email.message_id,
                    "conversation_id": email.conversation_id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "receivers": email.receivers,
                    "cc": email.cc,
                    "bcc": email.bcc,
                    "body": email.body,
                    "is_read": email.is_read,
                    "has_attachments": email.has_attachments,
                    "received_date": email.received_date.isoformat(),
                }
                for email in emails
            ],
        }

    return router
