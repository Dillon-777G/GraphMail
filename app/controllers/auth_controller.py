# Python standard library imports
import logging
from typing import Dict, Optional, Union

# Third party imports
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

# Application imports
from app.controllers.fAPI_dependencies.auth_dependency import AuthDependency
from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException
from app.service.graph.graph_authentication_service import Graph
from app.service.session_store.session_store_service import SessionStore

def auth_controller(graph: Graph, session_store: SessionStore) -> APIRouter:
    router = APIRouter()
    auth = AuthDependency(graph)
    logger = logging.getLogger(__name__)

    @router.get("/auth")
    async def initiate_auth(
        order_id: Optional[int] = None,
        auth_response: Union[Dict[str,str], None] = Depends(auth)):
        """
        Provides the authorization URL for the user to initiate authentication.
        """
        logger.info("Received direct auth request.")
        if auth_response:
            if order_id:
                logger.info("Received order ID, storing it in session.")
                state = auth_response["auth_url"].split("state=")[1].split("&")[0]
                session_store.store_order_id(state, order_id)
            logger.info("Received auth response, returning it.")
            return auth_response

        logger.info("No auth response, User is authenticated.")
        return {"authenticated": True, "auth_url": None}


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
