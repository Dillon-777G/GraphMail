import logging

from fastapi import APIRouter, Request

from app.service.email_service import EmailService
from app.service.graph_service import Graph

logger = logging.getLogger(__name__)

def email_controller(graph: Graph, email_service: EmailService) -> APIRouter:
    router = APIRouter()

    @router.get("/emails")
    async def get_emails(request: Request, folder_name: str):
        """
        Fetch emails from a specified folder. Handles authentication if necessary.
        """
        auth_status = graph.ensure_authenticated(request.query_params.get("code"))
        if not auth_status["authenticated"]:
            return {"status": "Authentication required", "auth_url": auth_status["auth_url"]}

        # Fetch emails from the specified folder
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
