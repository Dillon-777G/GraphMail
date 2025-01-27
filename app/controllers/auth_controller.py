import logging

from fastapi import APIRouter, Request

from app.service.graph_service import Graph
from app.exception.exceptions import AuthenticationFailedException

logger = logging.getLogger(__name__)

def auth_controller(graph: Graph) -> APIRouter:
    router = APIRouter()

    @router.get("/auth")
    def initiate_auth():
        """
        Provides the authorization URL for the user to initiate authentication.
        """
        auth_url = graph.get_authorization_url()
        return {
            "status": "success",
            "data": {
                "auth_url": auth_url
            }
        }

    @router.get("/callback")
    async def auth_callback(request: Request):
        """
        Handles the callback after user authentication.
        Exchanges the authorization code for tokens and confirms authentication.

        Raises:
            AuthenticationFailedException: If authentication fails or code is missing
        """
        authorization_code = request.query_params.get('code')
        if not authorization_code:
            raise AuthenticationFailedException(
                detail="Authorization code not provided",
                status_code=400
            )

        # Exchange code for token - will raise AuthenticationFailedException if it fails
        graph.exchange_code_for_token(authorization_code)
        
        return {
            "status": "success",
            "data": {
                "message": "Authentication successful"
            }
        }

    return router
