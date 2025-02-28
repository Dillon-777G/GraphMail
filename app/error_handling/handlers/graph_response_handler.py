# Third party imports
from fastapi import Request
from fastapi.responses import JSONResponse

# Local imports
from app.error_handling.exceptions.graph_response_exception import GraphResponseException
from app.error_handling.handlers.base_handler import BaseExceptionHandler

class GraphResponseHandler(BaseExceptionHandler):
    async def handle_graph_response_error(self, request: Request, exc: GraphResponseException):
        self._log_error(request, exc)
        response = self._create_base_response(request, exc, "graph_response_error")
        response["response_type"] = exc.response_type
        return JSONResponse(status_code=exc.status_code, content=response) 