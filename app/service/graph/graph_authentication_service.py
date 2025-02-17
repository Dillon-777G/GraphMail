import logging
import os
from typing import Optional, Dict, Any
import secrets
from datetime import datetime, timedelta

from azure.identity import AuthorizationCodeCredential
from msgraph import GraphServiceClient

from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException

"""
SUMMARY:

I have set this authentication class up to include a state tracker. This state tracking 
functionality protects us against CSRF and Replay attacks. It also helps the user generally
by preventing reusing the same Auth data, blocking conflicting auth requests, ensuring
that only fresh tokens are used, and preventing cache poisoning. I would recommend keeping it in place.

"""
class Graph:
    """Handles Microsoft Graph API client setup and authentication."""

    def __init__(self):
        """
        Initializes the Graph API client with environment variables.
        Sets up initial state with no active client connection.
        """
        # Group Azure configuration into a single dictionary
        self.config = {
            "client_id": os.getenv("AZURE_CLIENT_ID"),
            "client_secret": os.getenv("AZURE_CLIENT_SECRET"),
            "tenant_id": os.getenv("AZURE_TENANT_ID"),
            "redirect_uri": os.getenv("AZURE_REDIRECT_URI"),
            "scopes": os.getenv("AZURE_GRAPH_USER_SCOPES", "").split(" ")
        }
        self.client: Optional[GraphServiceClient] = None
        self.credential: Optional[AuthorizationCodeCredential] = None
        self.logger = logging.getLogger(__name__)
        self._state_store: Dict[str, datetime] = {}  # Store states with timestamps
        self.STATE_TIMEOUT = 300  # 5 minutes timeout for states # pylint: disable=invalid-name

        # init check
        self .is_loaded()
        

    def _cleanup_expired_states(self):
        """Remove expired states from the store"""
        current_time = datetime.utcnow()
        expired_states = [
            state for state, timestamp in self._state_store.items()
            if current_time - timestamp > timedelta(seconds=self.STATE_TIMEOUT)
        ]
        for state in expired_states:
            self._state_store.pop(state, None)

    def get_authorization_url(self) -> str:
        """
        Generates the OAuth2 authorization URL with state parameter for additional security.
        
        The state parameter helps prevent CSRF attacks and ensures the auth flow starts
        and ends with the same client.
        """
        # Generate a secure random state
        state = secrets.token_urlsafe(32)
        print(f"state: {state}")
        # Store state with timestamp
        self._state_store[state] = datetime.utcnow()
        self._cleanup_expired_states()
        
        self.logger.debug("Generated state: %s", state)
        self.logger.debug("Stored states after adding new one: %s", list(self._state_store.keys()))

        # Build authorization URL with state parameter
        base_url = f"https://login.microsoftonline.com/{self.config['tenant_id']}/oauth2/v2.0/authorize"
        params = {
            "client_id": self.config["client_id"],
            "response_type": "code",
            "redirect_uri": self.config["redirect_uri"],
            "response_mode": "query",
            "scope": " ".join(self.config["scopes"]),
            "state": state,
            "prompt": "select_account",      # forces user to select account everytime 
            "login_hint": "",      # Clears previous login hints
            "domain_hint": ""
        }
        
        query_string = "&".join(f"{key}={value}" for key, value in params.items())
        self.logger.info(f"Authorization URL generated successfully with state parameter:\n{base_url}?{query_string}") # pylint: disable=W1203
        return f"{base_url}?{query_string}"


    def verify_state(self, received_state: Optional[str]) -> bool:
        """Verify the received state matches a stored state and hasn't expired."""
        self.logger.debug("Verifying state: %s", received_state)
        self.logger.debug("Current store contents: %s", list(self._state_store.keys()))
        
        if not received_state:
            self.logger.debug("No state received, skipping verification")
            return False
            
        if received_state not in self._state_store:
            self.logger.warning("State not found in store: %s", received_state)
            self.logger.debug("Available states: %s", list(self._state_store.keys()))
            return False
                
        state_time = self._state_store[received_state]
        current_time = datetime.utcnow()
        is_valid = (current_time - state_time) <= timedelta(seconds=self.STATE_TIMEOUT)
        
        if not is_valid:
            self.logger.warning("State expired. Created: %s, Current: %s", 
                            state_time, current_time)
        
        self._state_store.pop(received_state)
        return is_valid

    async def exchange_code_for_token(self, authorization_code: str, state: Optional[str] = None):
        """
        Exchanges the authorization code for an access token with state verification.
        
        Args:
            authorization_code: The authorization code received from the callback
            state: The state parameter received from the callback
            
        Raises:
            AuthenticationFailedException: If state verification fails or token exchange fails
        """
        # Verify state parameter
        if not self.verify_state(state):
            raise AuthenticationFailedException(
                detail="Invalid or expired state parameter",
                status_code=400
            )

        try:
            self.credential = AuthorizationCodeCredential(
                tenant_id=self.config["tenant_id"],
                client_id=self.config["client_id"],
                authorization_code=authorization_code,
                redirect_uri=self.config["redirect_uri"],
                client_secret=self.config["client_secret"],
            )
            self.client = GraphServiceClient(self.credential, self.config["scopes"])
            self.logger.info("Graph client initialized successfully")


        except Exception as e:
            self.logger.error("Failed to exchange code for token: %s", e)
            # Clear potentially corrupted state
            self.client = None
            self.credential = None
            raise AuthenticationFailedException(
                detail="Failed to exchange authorization code for access token."
            ) from e


    async def ensure_authenticated(self, authorization_code: Optional[str] = None, state: Optional[str] = None) -> Dict[str, Any]:
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
        self.logger.info("Ensuring Graph client is authenticated.")

        if self.client and self.credential:
            self.logger.info("Graph client is already authenticated.")
            return {"authenticated": True, "auth_url": None}

        if not authorization_code:
            auth_url = self.get_authorization_url()
            return {
                "authenticated": False,
                "auth_url": auth_url,
            }

        try:
            # Exchange the authorization code for a token
            await self.exchange_code_for_token(authorization_code, state)
            self.logger.info("Successfully authenticated the Graph client.")
            return {"authenticated": True, "auth_url": None}
        except AuthenticationFailedException as e:
            self.logger.error("Authentication failed: %s", e)
            raise


    def is_loaded(self):
        if not all([self.config["client_id"], self.config["client_secret"],
            self.config["tenant_id"], self.config["redirect_uri"]]):
            self.logger.error(
                """
                Missing required environment variables:
                AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID, AZURE_REDIRECT_URI
                """
            )
            raise ValueError("Missing required environment variables for Graph API authentication")
        self.logger.info("env has loaded successfully, proceeding")
