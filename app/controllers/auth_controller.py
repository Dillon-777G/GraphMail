import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.service.graph.graph_authentication_service import Graph
from app.service.session_store.session_store_service import SessionStore
from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException

def auth_controller(graph: Graph, session_store: SessionStore) -> APIRouter:
    router = APIRouter()
    logger = logging.getLogger(__name__)

    @router.get("/auth")
    def initiate_auth():
        """
        Provides the authorization URL for the user to initiate authentication.
        """
        logger.info("Received direct auth request, certainly hope you are a developer.")
        auth_url = graph.get_authorization_url()
        logger.info("Initiating auth with URL: %s", auth_url)
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
        Exchanges the authorization code for tokens and redirects to bridge URL.
        """
        logger.info("Received auth callback, time to send you back to northstar.")
        authorization_code = request.query_params.get('code')
        state = request.query_params.get('state')
        
        if not authorization_code:
            logger.error("Authorization code not provided")
            raise AuthenticationFailedException(
                detail="Authorization code not provided",
                status_code=400
            )

        if not state:
            logger.error("State parameter is missing in callback")
            raise AuthenticationFailedException(
                detail="State parameter is missing in callback",
                status_code=400
            )

        # Exchange code for token
        await graph.exchange_code_for_token(authorization_code, state)
        
        # Get order_id from session store
        order_id = session_store.get_order_id(state)
        if not order_id:
            # The user should never be hitting these endpoints without being authenticated already
            logger.warning("No order ID found for this session, you probably shouldn't be seeing this. I'm kicking you back to homepage.")
            return RedirectResponse(url="http://localhost:3000/")
        # Clean up the session
        session_store.remove_session(state)
        logger.info("Session cleaned up, redirecting to bridge URL with order ID: %s", order_id)
        # Redirect to bridge URL with order ID
        redirect_url = f"http://localhost:3000/bridge/{order_id}"
        return RedirectResponse(url=redirect_url)

    return router
