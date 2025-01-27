import logging
import os
from typing import Optional, Dict, Any
from azure.identity import AuthorizationCodeCredential
from msgraph import GraphServiceClient
from app.exception.exceptions import AuthenticationFailedException

logger = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods
class Graph:
    """Handles Microsoft Graph API client setup and authentication."""

    def __init__(self):
        """
        Initializes the Graph API client with environment variables.
        Sets up initial state with no active client connection.
        """
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.tenant_id = os.getenv("TENANT_ID")
        self.redirect_uri = os.getenv("REDIRECT_URI")

        self.scopes = os.getenv("AZURE_GRAPH_USER_SCOPES", "").split(" ")
        self.client: Optional[GraphServiceClient] = None
        self.credential: Optional[AuthorizationCodeCredential] = None

        # Validate required environment variables
        if not all([self.client_id, self.client_secret, self.tenant_id, self.redirect_uri]):
            logger.error(
                """
                Missing required environment variables:
                CLIENT_ID, CLIENT_SECRET, TENANT_ID, REDIRECT_URI
                """
            )
            raise ValueError("Missing required environment variables for Graph API authentication.")

    def get_authorization_url(self) -> str:
        """
        Generates the OAuth2 authorization URL for Microsoft Graph API.

        Returns:
            str: The complete authorization URL with all necessary parameters.
        """
        base_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self.scopes),
        }
        query_string = "&".join(
            f"{key}={value}" for key, value in params.items()
        )
        logger.info("Authorization URL generated successfully.")
        return f"{base_url}?{query_string}"

    def exchange_code_for_token(self, authorization_code: str):
        """
        Exchanges the authorization code for an access token and initializes the Graph client.

        Args:
            authorization_code (str): The authorization code received from the callback endpoint.

        Raises:
            AuthenticationFailedException: If token exchange or client initialization fails.
        """
        try:
            self.credential = AuthorizationCodeCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                authorization_code=authorization_code,
                redirect_uri=self.redirect_uri,
                client_secret=self.client_secret,
            )
            self.client = GraphServiceClient(self.credential, self.scopes)  # type: ignore
            logger.info("Graph client initialized successfully.")
        except Exception as e:
            logger.error("Failed to exchange code for token: %s", e)
            raise AuthenticationFailedException(
                detail="Failed to exchange authorization code for access token."
            ) from e

    def ensure_authenticated(self, authorization_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Ensures the Graph client is authenticated. If not initialized
        and an authorization code is provided, exchanges it for a token.
        Otherwise, returns an auth URL for user authentication.

        Args:
            authorization_code (Optional[str]): The authorization code to exchange for a token.

        Returns:
            dict: A response indicating whether authentication
            is required, including the authorization URL if
            needed.

        Raises:
            AuthenticationFailedException: If authentication fails.
        """
        logger.info("Ensuring Graph client is authenticated.")

        if self.client and self.credential:
            logger.info("Graph client is already authenticated.")
            return {"authenticated": True, "auth_url": None}

        if not authorization_code:
            auth_url = self.get_authorization_url()
            logger.warning(
                "Authentication required. Redirecting to authorization URL."
            )
            return {
                "authenticated": False,
                "auth_url": auth_url,
            }

        try:
            # Exchange the authorization code for a token
            self.exchange_code_for_token(authorization_code)
            logger.info("Successfully authenticated the Graph client.")
            return {"authenticated": True, "auth_url": None}
        except AuthenticationFailedException as e:
            logger.error("Authentication failed: %s", e)
            raise

# End of file
