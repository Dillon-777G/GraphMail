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
            # Always check authentication status first
            auth_status = await self.graph.ensure_authenticated()
            if not auth_status["authenticated"]:
                self.logger.info("User not authenticated or token expired, redirecting to auth URL.")
                return auth_status

            return None  # Continue request - we're authenticated

        except Exception as e:
            self.logger.error("Authentication error: %s", str(e))
            raise AuthenticationFailedException(
                detail="Authentication service error",
                status_code=500
            ) from e
