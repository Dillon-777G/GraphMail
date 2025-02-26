from typing import Union, Dict, Any
import logging

from fastapi import APIRouter, Depends, Body


from app.service.emails.select_email_service import SelectEmailService
from app.service.graph.graph_authentication_service import Graph
from app.controllers.fAPI_dependencies.auth_dependency import AuthDependency
from app.models.dto.email_selection_dto import EmailSelectionDTO

def email_controller(
    graph: Graph,
    select_email_service: SelectEmailService
) -> APIRouter:
    router = APIRouter()
    auth = AuthDependency(graph)
    logger = logging.getLogger(__name__)

    @router.post("/{folder_id}/select")
    async def get_selected_emails(
        folder_id: str,
        selection: EmailSelectionDTO = Body(...),
        auth_response: Union[Dict[str,str], None] = Depends(auth)
    ) -> Dict[str, Any]:
        """
        Fetch specific emails by their IDs and return them as DBEmail objects.

        Args:
            folder_id (str): The ID of the folder containing the emails (from path)
            selection (EmailSelectionDTO): Selection parameters including message IDs and reference info
            auth_response: Authentication response from dependency

        Returns:
            Dict[str, Any]: A dictionary containing the status of the operation and the data
            returned from the select and persist operation.

            NOTE: 
            - The successful ids are the email ids in the database
            - the duplicate ids are the graph message ids
            - the failure ids are the graph source ids
        """
        if auth_response:
            return auth_response

        logger.info(
            "Received request to fetch specific emails from folder ID: %s, Message IDs: %s",
            folder_id,
            selection.email_source_ids
        )

        successful_emails, duplicate_emails, failed_emails = await select_email_service.select_and_persist_emails(
            folder_id=folder_id,
            selection=selection
        )

        total_emails = len(successful_emails) + len(duplicate_emails) + len(failed_emails)
        
        return {
            "status": "success",
            "data": {
                "total_emails": total_emails,
                "successful": successful_emails,
                "duplicates": duplicate_emails,
                "failures": failed_emails
            }
        }

    return router 