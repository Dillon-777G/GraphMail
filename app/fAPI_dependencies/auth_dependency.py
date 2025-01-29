from fastapi import Request
from starlette.responses import RedirectResponse  # Import from Starlette
from typing import Union, Optional, Dict, Any
import logging

from app.service.graph_service import Graph
from app.exception.exceptions import AuthenticationFailedException

logger = logging.getLogger(__name__)

class AuthDependency:
    def __init__(self, graph: Graph):
        self.graph = graph

    async def __call__(self, request: Request) -> Optional[RedirectResponse]:
        """Return None if authenticated, else return a RedirectResponse."""

        if not request:
            raise AuthenticationFailedException(
                detail="Request object is missing or invalid.",
                status_code=400
            )

        try:
            auth_code = request.query_params.get("code")
            auth_status = self.graph.ensure_authenticated(auth_code)

            if not auth_status["authenticated"]:
                # If not authenticated, redirect the user to the auth URL
                logger.info("Authentication required, redirecting to auth URL")
                return RedirectResponse(url=auth_status["auth_url"])

            # If authenticated, return None so the endpoint can continue.
            return None

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise AuthenticationFailedException(
                detail="Authentication service error",
                status_code=500
            )
