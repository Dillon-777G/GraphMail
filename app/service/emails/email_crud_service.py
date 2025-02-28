# Python standard library imports
import logging

# Application imports
from app.repository.email_repository import EmailRepository

logger = logging.getLogger(__name__)

class EmailCRUDService:
    def __init__(self, email_repository: EmailRepository):
        self.logger = logging.getLogger(__name__)
        self.email_repository = email_repository

    async def get_email_id_by_graph_message_id(self, graph_message_id: str) -> int:
        """
        Get the database ID for an email using its graph message ID.
        
        Args:
            graph_message_id (str): The Microsoft Graph message ID
            
        Returns:
            int: The database ID of the email
            
        Raises:
            NoResultFound: If the email cannot be found or retrieved
            EmailPersistenceException: If there is an unexpected error
        """
        return await self.email_repository.get_email_id_by_graph_message_id(graph_message_id)
