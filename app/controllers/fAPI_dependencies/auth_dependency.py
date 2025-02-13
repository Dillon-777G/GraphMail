from typing import Optional, Dict
import logging

from fastapi import Request

from app.service.graph.graph_authentication_service import Graph
from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException

class AuthDependency:
    def __init__(self, graph: Graph):
        self.graph = graph
        self.logger = logging.getLogger(__name__)

    async def __call__(self, request: Request) -> Optional[Dict[str, str]]:
        """Handles authentication before processing a request."""

        if not request:
            raise AuthenticationFailedException(
                detail="Request object is missing or invalid.",
                status_code=400
            )

        try:
            # If already authenticated, return None (continue request)
            if self.graph.client and self.graph.credential:
                return None

            auth_code = request.query_params.get("code")
            state = request.query_params.get("state")
            self.logger.debug(f"State in auth dep: {state}")

            if auth_code and state:
                self.logger.debug("Auth callback detected - Code and State present.")

                auth_status = await self.graph.ensure_authenticated(auth_code, state)

                if auth_status["authenticated"]:
                    self.logger.info("User successfully authenticated.")
                    return None  # Continue request

                self.logger.warning("Authentication failed despite valid code and state.")
                return {
                    "status": "Authentication error",
                    "auth_url": auth_status["auth_url"],
                }

            # If not authenticated and no code/state, redirect to auth URL
            self.logger.info("User not authenticated, redirecting to auth URL.")
            return {
                "status": "Authentication required",
                "auth_url": self.graph.get_authorization_url(),
            }

        except Exception as e:
            self.logger.error("Authentication error: %s", str(e))
            raise AuthenticationFailedException(
                detail="Authentication service error",
                status_code=500
            ) from e
