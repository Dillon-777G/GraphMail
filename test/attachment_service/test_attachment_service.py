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
    async def setup(self):
        # Create a mock GraphServiceClient
        mock_graph_client = MagicMock()

        # Mock asynchronous methods
        mock_graph_client.me.messages.post = AsyncMock()
        mock_graph_client.me.messages.by_message_id = MagicMock()
        mock_graph_client.me.mail_folders.get = AsyncMock()
        mock_graph_client.me.mail_folders.by_mail_folder_id = MagicMock()

        # Mock the Graph class
        graph_service = Graph()
        graph_service.client = mock_graph_client

        # Create dependencies
        graph_utils = GraphUtils(graph_service)
        attachment_service = AttachmentService(graph_utils)

        return attachment_service, graph_utils

    async def test_get_message_attachments_filters_correctly(self, setup):
        attachment_service, graph_utils = setup

        # Create the test_files directory if it doesn't exist
        test_files_dir = Path(__file__).parent / "test_files"
        test_files_dir.mkdir(parents=True, exist_ok=True)

        # Create a test file attachment
        test_file_path = test_files_dir / "test.txt"
        with open(test_file_path, "w") as f:
            f.write("Test content")

        # Mock sending a test email
        mock_message_id = "mockMessageId"
        sent_message_mock = AsyncMock()
        sent_message_mock.id = mock_message_id
        graph_utils.graph.client.me.messages.post.return_value = sent_message_mock

        # Mock retrieving mail folders
        mock_folder_id = "mockFolderId"
        graph_utils.graph.client.me.mail_folders.get.return_value.value = [
            MagicMock(display_name="order3", id=mock_folder_id)
        ]

        # Mock moving the message
        move_mock = AsyncMock()
        graph_utils.graph.client.me.messages.by_message_id(mock_message_id).move.post = move_mock

        # Create real Attachment objects
        file_attachment = FileAttachment()
        file_attachment.name = "test.txt"
        file_attachment.odata_type = "#microsoft.graph.fileAttachment"

        item_attachment = ItemAttachment()
        item_attachment.name = "Test Email"
        item_attachment.odata_type = "#microsoft.graph.itemAttachment"

        # Mock AttachmentCollectionResponse
        def mock_filtered_response(request_configuration=None):
            # Check for query parameters
            if request_configuration and request_configuration.query_parameters:
                filter_value = request_configuration.query_parameters.get("$filter")
                # Simulate filtering
                if filter_value == "odata.type eq '#microsoft.graph.fileAttachment'":
                    return AttachmentCollectionResponse(value=[file_attachment])
            return AttachmentCollectionResponse(value=[file_attachment, item_attachment])

        # Mock retrieving attachments
        graph_utils.graph.client.me.mail_folders.by_mail_folder_id.return_value.messages.by_message_id.return_value.attachments.get = AsyncMock(
            side_effect=mock_filtered_response
        )

        # Test the method
        attachments = await attachment_service.get_message_attachments("order3", mock_message_id)

        # Verify only file attachments are returned
        assert len(attachments) == 1
        assert attachments[0].name == "test.txt"

        # Cleanup
        os.remove(test_file_path)
