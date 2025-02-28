# Python standard library imports
import json
from unittest.mock import AsyncMock, MagicMock, patch

# Third party imports
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from kiota_abstractions.api_error import APIError
from sqlalchemy.exc import NoResultFound

# Application imports
# Controllers
from app.controllers.recursive_email_controller import recursive_email_controller

# Error handling
from app.error_handling.exception_handler_manager import ExceptionHandlerManager
from app.error_handling.exceptions.attachment_persistence_exception import AttachmentPersistenceException
from app.error_handling.exceptions.authentication_exception import AuthenticationFailedException
from app.error_handling.exceptions.db_email_recipient_exception import DBEmailRecipientException
from app.error_handling.exceptions.email_attachment_exception import EmailAttachmentException
from app.error_handling.exceptions.email_persistence_exception import EmailPersistenceException
from app.error_handling.exceptions.folder_exception import FolderException
from app.error_handling.exceptions.graph_response_exception import GraphResponseException
from app.error_handling.exceptions.id_translation_exception import IdTranslationException
from app.error_handling.exceptions.recursive_email_exception import RecursiveEmailException

# Update VALID_PAYLOAD to include all required fields.
VALID_PAYLOAD = {
    "ref_type": "test",
    "ref_id": "123",
    "created_by": "123",
    "test": "dummy"  # added required field
}

# Helper: creates an async generator that always raises the given exception.
def make_failing_generator(exception_instance):
    async def failing_generator(folder_id, email_request): # pylint: disable=unused-argument
        raise exception_instance
        yield # pylint: disable=unreachable # dummy yield to mark this as an async generator
    return failing_generator

# Create dummy classes to patch AppStatus.
class DummyEvent:
    async def wait(self):
        return

class DummyAppStatus:
    should_exit_event = DummyEvent()
    @property
    def should_exit(self):
        return False

# Parameterize with different exception instances and expected message substrings.
@pytest.mark.parametrize(
    "exception_instance, expected_message_substring",
    [
        (APIError(message="Test API error", response_status_code=400), "Test API error"),
        (AttachmentPersistenceException(detail="Test attachment persistence error"), "Test attachment persistence error"),
        (AuthenticationFailedException(detail="Test auth error", status_code=401), "Test auth error"),
        (DBEmailRecipientException("Test db email recipient error"), "Test db email recipient error"),
        (EmailAttachmentException(detail="Test attachment error", attachment_id="att123"), "Test attachment error"),
        (EmailPersistenceException(detail="Test email persistence error", message_ids=["msg1"]), "Test email persistence error"),
        (FolderException("Test folder error", folder_id="folder1"), "Test folder error"),
        (GraphResponseException(detail="Test graph response error", response_type="MessageCollectionResponse"), "Test graph response error"),
        (IdTranslationException(detail="Test id translation error", source_ids=["id1"]), "Test id translation error"),
        (NoResultFound("Test no result found error"), "Test no result found error"),
        (RecursiveEmailException(detail="Test recursive email error", folder_id="folder2"), "Test recursive email error"),
        (RequestValidationError([{"loc": ("body", "test"), "msg": "field required", "type": "value_error.missing"}]), "field required"),
        (ValueError("Test value error occurred"), "Test value error occurred")
    ]
)



def test_sse_error_handler_for_all_exceptions(exception_instance, expected_message_substring):
    # Instantiate the real ExceptionHandlerManager.
    manager = ExceptionHandlerManager()

    # Create dependencies and services
    graph = MagicMock()

    # Mock the graph ensure_authenticated method.
    graph.ensure_authenticated = AsyncMock(return_value={"authenticated": True, "auth_url": None})

    # Mock the recursive email service. Make a service that always raises the given exception.
    recursive_email_service = MagicMock()
    recursive_email_service.get_all_emails_recursively = make_failing_generator(exception_instance)

    # Test the endpoint, must mock the auth dependency and the AppStatus. SSE reads app status, we need it
    with patch("app.controllers.fAPI_dependencies.auth_dependency.AuthDependency") as mock_auth_dependency,   \
        patch("sse_starlette.sse.AppStatus", new=DummyAppStatus()):
        mock_auth_instance = mock_auth_dependency.return_value
        mock_auth_instance.__call__ = AsyncMock(return_value=None)

        # Setup app and client
        app = FastAPI()
        app.include_router(recursive_email_controller(graph, recursive_email_service, manager))
        
        # Test the endpoint and collect events
        events = []
        client = TestClient(app)
        with client.stream("POST", "/folder/test_folder/all_emails", json=VALID_PAYLOAD) as response:
            for line in response.iter_lines():
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if line.startswith("data:"):
                    try:
                        events.append(json.loads(line[len("data:"):].strip()))
                    except Exception as e: # pylint: disable=broad-exception-caught # we can ignore this in a test
                        print("Error decoding line:", line, e)
        
        # Verify results
        error_event = next((event for event in events if event.get("status") == "error"), None)
        assert error_event is not None, f"No error event found for exception: {exception_instance}"
        assert expected_message_substring in error_event.get("message", ""), (
            f"Expected '{expected_message_substring}' in error message, got: {error_event.get('message')}"
        )
