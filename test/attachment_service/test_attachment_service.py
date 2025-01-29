from unittest.mock import AsyncMock, MagicMock
from msgraph.generated.models.attachment_collection_response import AttachmentCollectionResponse
from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.models.item_attachment import ItemAttachment
from app.service.graph_service import Graph
from app.utils.graph_utils import GraphUtils
from app.service.attachment_service import AttachmentService
import pytest
import os
from pathlib import Path


class TestAttachmentService:
    @pytest.fixture
    async def setup(self, monkeypatch):
        # Mock environment variables needed for Graph authentication
        monkeypatch.setenv("AZURE_CLIENT_ID", "mock_client_id")
        monkeypatch.setenv("AZURE_CLIENT_SECRET", "mock_client_secret")
        monkeypatch.setenv("AZURE_TENANT_ID", "mock_tenant_id")
        monkeypatch.setenv("AZURE_REDIRECT_URI", "mock_redirect_uri")
        
        # Create the base mock client that will be the root of our mock chain
        mock_graph_client = MagicMock()

        # Set up the Graph service with our mock client
        graph_service = Graph()
        graph_service.client = mock_graph_client
        # Mock authentication to always return success without actually authenticating
        graph_service.ensure_authenticated = MagicMock(return_value={"authenticated": True})

        # Build the mock chain from bottom to top
        # This mirrors the actual API chain: 
        # client.me.mail_folders.by_mail_folder_id().messages.by_message_id().get()
        
        # First, create a mock message that will be returned by the final get() call
        mock_message = MagicMock()
        # The get() method is async, so we use AsyncMock for it
        mock_get = AsyncMock(return_value=mock_message)
        
        # Create the by_message_id object that has the get method
        mock_by_message_id = MagicMock()
        mock_by_message_id.get = mock_get
        
        # Create the messages object that has the by_message_id method
        mock_messages = MagicMock()
        mock_messages.by_message_id = MagicMock(return_value=mock_by_message_id)
        
        # Create the folder object that has the messages attribute
        mock_folder = MagicMock()
        mock_folder.messages = mock_messages
        
        # Set up the mail folders mock chain
        # The get() for listing folders needs to be async
        mock_graph_client.me.mail_folders.get = AsyncMock()
        # by_mail_folder_id returns our mock folder
        mock_graph_client.me.mail_folders.by_mail_folder_id = MagicMock(return_value=mock_folder)

        # Create the actual service objects using our mocked dependencies
        graph_utils = GraphUtils(graph_service)
        attachment_service = AttachmentService(graph_utils)

        return attachment_service, graph_utils

    async def test_get_message_attachments_filters_correctly(self, setup):
        attachment_service, graph_utils = setup

        # Set up test file directory for attachment simulation
        test_files_dir = Path(__file__).parent / "test_files"
        test_files_dir.mkdir(parents=True, exist_ok=True)

        # Create a sample test file
        test_file_path = test_files_dir / "test.txt"
        with open(test_file_path, "w") as f:
            f.write("Test content")

        # Mock the folder listing response
        # When get_folder_id_by_name is called, it will find this folder
        mock_folder_id = "mockFolderId"
        mock_folder = MagicMock(display_name="order3", id=mock_folder_id)
        graph_utils.graph.client.me.mail_folders.get.return_value = MagicMock(value=[mock_folder])

        # Create a sample file attachment that we expect to be returned
        file_attachment = FileAttachment()
        file_attachment.id = "test-attachment-id"
        file_attachment.name = "test.txt"
        file_attachment.content_type = "text/plain"
        file_attachment.size = 123
        file_attachment.is_inline = False
        file_attachment.odata_type = "#microsoft.graph.fileAttachment"

        # Create a sample item attachment that should be filtered out
        item_attachment = ItemAttachment()
        item_attachment.name = "Test Email"
        item_attachment.odata_type = "#microsoft.graph.itemAttachment"

        # Set up the message that will be returned by the API
        mock_message = MagicMock()
        mock_message.attachments = [file_attachment, item_attachment]
        
        # Configure the mock chain to return our message
        graph_utils.graph.client.me.mail_folders.by_mail_folder_id().messages.by_message_id().get.return_value = mock_message

        # Execute the method we're testing
        attachments = await attachment_service.get_message_attachments("order3", "mockMessageId")

        # Verify that only file attachments were returned (item attachment filtered out)
        assert len(attachments) == 1
        assert attachments[0].name == "test.txt"

        # Verify that the API was called with the correct parameters
        get_message_mock = graph_utils.graph.client.me.mail_folders.by_mail_folder_id().messages.by_message_id().get
        assert get_message_mock.called
        request_config = get_message_mock.call_args[1]['request_configuration']
        assert request_config.query_parameters == {"expand": ["attachments"]}

        # Clean up the test file
        os.remove(test_file_path)
