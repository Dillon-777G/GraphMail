# Python standard library imports
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

# Third party imports
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Application imports
from app.controllers.recursive_email_controller import recursive_email_controller
from app.logging.logging_config import setup_logging

# A dummy response to simulate what an exception handler returns.
class DummyResponse:
    def __init__(self, content: dict):
        self.body = json.dumps(content).encode('utf-8')


def test_sse_event_generator_handles_exception(): # pylint: disable=too-many-locals
    # Create a dummy "graph" dependency.
    setup_logging()
    logger = logging.getLogger(__name__)
    graph = MagicMock()
    

    graph.ensure_authenticated = AsyncMock(return_value={"authenticated": True, "auth_url": None})
    
    # Create a fake recursive email service whose async generator immediately raises an exception.
    recursive_email_service = MagicMock()
    async def failing_generator(folder_id, email_request): # pylint: disable=unused-argument
        raise ValueError("Test error occurred")
        yield # pylint: disable=unreachable # dummy yield
    recursive_email_service.get_all_emails_recursively = failing_generator



    # Set up a mock exception handler manager.
    exception_handler_manager = MagicMock()
    dummy_error_content = {"detail": "Test error detail", "type": "server_error"}
    dummy_response = DummyResponse(dummy_error_content)
    # Simulate that the ValueError is handled by the value error handler.
    exception_handler_manager.handle_value_error = AsyncMock(return_value=dummy_response)
    # Also provide a fallback for global errors.
    exception_handler_manager.handle_global_error = AsyncMock(return_value=dummy_response)

    # Mock the AuthDependency class
    with patch("app.controllers.fAPI_dependencies.auth_dependency.AuthDependency") as mock_auth_dependency:
        # Configure the mock to return None when called (successful auth)
        mock_auth_instance = mock_auth_dependency.return_value
        mock_auth_instance.__call__ = AsyncMock(return_value=None)

        # Create the router using your controller.
        router = recursive_email_controller(graph, recursive_email_service, exception_handler_manager)

        # Build a minimal FastAPI app and include our router.
        app = FastAPI()
        app.include_router(router)

        client = TestClient(app)
        
        # Trigger the SSE endpoint.
        with client.stream("POST", "/folder/test_folder/all_emails", 
        json={
                "ref_type": "test",
                "ref_id": "123",
                "created_by": "123"
            }) as response:
            events = []
            for line in response.iter_lines():
                # Decode bytes to string if necessary.
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                logger.info("Raw line: %s", line)  # Debug: print each raw line from the stream.
                if line.startswith("data:"):
                    try:
                        event_data = json.loads(line[len("data:"):].strip())
                        events.append(event_data)
                    except Exception as e: # pylint: disable=broad-exception-caught
                        logger.info("Error decoding line: %s, %s", line, e)
        
        logger.info("Captured events: %s", events)




        # # Look for the error event in the yielded SSE messages.
        error_event = next((event for event in events if event.get("status") == "error"), None)
        
        assert error_event is not None, "No error event found in SSE stream"
        assert error_event.get("message") == "Test error detail"
        assert error_event.get("type") == "server_error"
