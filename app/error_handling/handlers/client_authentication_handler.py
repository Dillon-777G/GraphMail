# Third party imports
from azure.core.exceptions import ClientAuthenticationError
from fastapi import Request
from fastapi.responses import JSONResponse

# Local imports
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class ClientAuthenticationHandler(BaseExceptionHandler):
    async def handle_client_authentication_error(
        self, 
        request: Request, 
        exc: ClientAuthenticationError
    ):
        """Handle Microsoft Graph client authentication errors.
        If we made it here, we have a problem.
        
        Issues here are directly related to the Microsoft Graph API and the
        refresh token functionality.
        """
        self._log_error(request, exc)
        
        response = self._create_base_response(
            request, 
            exc, 
            "client_authentication_error"
        )
        
        # Check for specific error codes in the error message
        if "AADSTS70008" in str(exc):
            response["error_code"] = "AADSTS70008"
            response["refresh_required"] = True
            response["detail"] = "Refresh token has expired. The application will force a new login."
            status_code = 401
        else:
            status_code = 500

        return JSONResponse(
            status_code=status_code,
            content=response
        ) 