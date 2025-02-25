import logging
import os
from typing import Optional, Dict, Any
import secrets
from datetime import datetime, timedelta

from azure.identity import AuthorizationCodeCredential
from azure.core.exceptions import ClientAuthenticationError
from msgraph import GraphServiceClient

from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException

"""
SUMMARY:

I have set this authentication class up to include a state tracker. This state tracking 
functionality protects us against CSRF and Replay attacks. It also helps the user generally
by preventing reusing the same Auth data, blocking conflicting auth requests, refreshing tokens,
and allowing for the refresh token to fail gracefully. This is done by clearing the client and 
credential when the refresh token fails, ensuring that only fresh tokens are used, and preventing
cache poisoning. I would recommend keeping it in place.

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
        self.token_expires_at: Optional[datetime] = None
        self.token_refresh_window = 300  # Refresh token 5 minutes before expiration

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

            # Retrieve token details and update expiration time.
            token_response = self.credential.get_token(*self.config["scopes"])
            self.token_expires_at = datetime.utcfromtimestamp(token_response.expires_on)
            
            self.logger.info("Graph client initialized successfully; token expires at %s", self.token_expires_at)


        except Exception as e:
            self.logger.error("Failed to exchange code for token: %s", e)
            # Clear potentially corrupted state
            self.client = None
            self.credential = None
            raise AuthenticationFailedException(
                detail="Failed to exchange authorization code for access token."
            ) from e


    async def refresh_token_if_needed(self) -> bool:
        """
        Refreshes the access token if it's close to expiration.
        Returns True if the token is still valid or refreshed successfully,
        and False if the token refresh fails (e.g. due to an expired refresh token).
        """
        if not self.credential or not self.token_expires_at:
            return False

        now = datetime.utcnow()
        time_remaining = (self.token_expires_at - now).total_seconds()
        
        # Only attempt a refresh if the token is within the refresh window.
        if time_remaining > self.token_refresh_window:
            self.logger.info("Token is still valid for %s seconds, no refresh needed.", time_remaining)
            return True

        try:
            # Refresh the token by calling get_token with unpacked scopes.
            token_response = await self.credential.get_token(*self.config["scopes"])
            if token_response.expires_on:
                self.token_expires_at = datetime.utcfromtimestamp(token_response.expires_on)
                self.logger.info("Token refreshed successfully; new expiration at %s", self.token_expires_at)
                return True
            self.logger.error("Token response did not contain an expiration time.")
            return False
        except ClientAuthenticationError as e:
            self.logger.error("Failed to refresh token: %s", e)
            if "AADSTS70008" in str(e):
                self.logger.info("Refresh token expired, clearing credentials to force new login.")
                self.client = None
                self.credential = None
            return False



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

        has_credentials = bool(self.client and self.credential)
        has_auth_code = bool(authorization_code)
        
        token_valid = False
        if self.token_expires_at:
            remaining = (self.token_expires_at - datetime.utcnow()).total_seconds()
            token_valid = remaining > self.token_refresh_window

        match (has_credentials, has_auth_code, token_valid):
            # Case 1: We have credentials and the token is valid.
            case (True, _, True):
                self.logger.info("Token is valid; no refresh needed.")
                return {"authenticated": True, "auth_url": None}
            
            # Case 2: We have credentials but token is near expiration.
            case (True, _, False):
                if await self.refresh_token_if_needed():
                    self.logger.info("Token refreshed successfully.")
                    return {"authenticated": True, "auth_url": None}
                self.logger.info("Token refresh failed; forcing new login.")
                return {"authenticated": False, "auth_url": self.get_authorization_url()}
            
            # Case 3: No credentials and no auth code provided.
            case (False, False, _):
                self.logger.info("No credentials and no auth code; initiating login flow.")
                return {"authenticated": False, "auth_url": self.get_authorization_url()}
            
            # Case 4: No credentials, but an auth code is provided.
            case (False, True, _):
                try:
                    await self.exchange_code_for_token(authorization_code, state)
                    self.logger.info("Successfully authenticated via auth code exchange.")
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
