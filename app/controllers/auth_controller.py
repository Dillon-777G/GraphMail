from fastapi import APIRouter, Request

from app.service.graph.graph_authentication_service import Graph
from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException

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
        state = request.query_params.get('state') 
        if not authorization_code:
            raise AuthenticationFailedException(
                detail="Authorization code not provided",
                status_code=400
            )

        if not state:
            raise AuthenticationFailedException(
                detail="State parameter is missing in callback",
                status_code =400
            )

        # Exchange code for token - will raise AuthenticationFailedException if it fails
        await graph.exchange_code_for_token(authorization_code, state)
        
        return {
            "status": "success",
            "data": {
                "message": "Authentication successful"
            }
        }

    return router
