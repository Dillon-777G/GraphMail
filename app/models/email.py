# Standard library imports
from datetime import datetime
from typing import List, Optional

# Third party imports
from bs4 import BeautifulSoup
from msgraph.generated.models.message_collection_response import MessageCollectionResponse
from pydantic import BaseModel, ConfigDict, Field

"""
SUMMARY:
This class is based on the business requirements of the email service
as well as the Microsoft Graph API.

For any specific details, please refer to the Microsoft Graph API documentation.

LINK: https://learn.microsoft.com/en-us/graph/api/resources/message?view=graph-rest-1.0
"""
class Email(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject: Optional[str] = "No Subject"
    sender: Optional[str] = "Unknown"
    receivers: List[str] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    bcc: List[str] = Field(default_factory=list)
    body: Optional[str] = ""
    conversation_id: Optional[str] = None
    is_read: bool = False
    has_attachments: bool = False
    received_date: datetime
    message_id: Optional[str]
    source_id: str
    attachment_types: List[str] = Field(default_factory=list)
    attachment_count: int = 0

    @classmethod
    def from_graph_message(cls, message: MessageCollectionResponse, immutable_id: str) -> "Email":
        """
        Converts a Microsoft Graph API MessageCollectionResponse into our Email model.

        Args:
            message (MessageCollectionResponse): The message to convert.
            immutable_id (str): The immutable ID of the message.

        Returns:
            Email: The converted Email model.
        """
        receivers = [
            recipient.email_address.name
            for recipient in (message.to_recipients or [])
            if recipient and recipient.email_address
        ]
        cc = [
            recipient.email_address.name
            for recipient in (message.cc_recipients or [])
            if recipient and recipient.email_address
        ]
        bcc = [
            recipient.email_address.name
            for recipient in (message.bcc_recipients or [])
            if recipient and recipient.email_address
        ]

        attachment_types, has_file_attachments, attachment_count = cls._get_attachment_info(message)
        has_inline_attachments = cls._has_inline_attachments(message.body.content)

        return cls(
            subject=message.subject or "No Subject",
            sender=(message.from_.email_address.name if message.from_ and message.from_.email_address else "Unknown"),
            receivers=receivers,
            cc=cc,
            bcc=bcc,
            body=message.body.content or "",
            received_date=message.received_date_time,
            conversation_id=message.conversation_id,
            is_read=message.is_read,
            has_attachments=has_file_attachments or has_inline_attachments,
            message_id=immutable_id,
            source_id=message.id,
            attachment_types=attachment_types,
            attachment_count=attachment_count,
        )

    # different constructor to use for paginated emails
    @classmethod
    def from_graph_message_without_id(cls, message: MessageCollectionResponse) -> "Email":
        """
        Converts a Microsoft Graph API MessageCollectionResponse into our Email model,
        without requiring an immutable ID. Uses the source_id as the message_id.

        Args:
            message (MessageCollectionResponse): The message to convert.

        Returns:
            Email: The converted Email model.
        """
        receivers = [
            recipient.email_address.name
            for recipient in (message.to_recipients or [])
            if recipient and recipient.email_address
        ]
        cc = [
            recipient.email_address.name
            for recipient in (message.cc_recipients or [])
            if recipient and recipient.email_address
        ]
        bcc = [
            recipient.email_address.name
            for recipient in (message.bcc_recipients or [])
            if recipient and recipient.email_address
        ]

        attachment_types, has_file_attachments, attachment_count = cls._get_attachment_info(message)
        has_inline_attachments = cls._has_inline_attachments(message.body.content)

        return cls(
            subject=message.subject or "No Subject",
            sender=(message.from_.email_address.name if message.from_ and message.from_.email_address else "Unknown"),
            receivers=receivers,
            cc=cc,
            bcc=bcc,
            body=message.body.content or "",
            received_date=message.received_date_time,
            conversation_id=message.conversation_id,
            is_read=message.is_read,
            has_attachments=has_file_attachments or has_inline_attachments,
            message_id=None,  # For now this is empty, to be later filled with immutable
            source_id=message.id,
            attachment_types=attachment_types,
            attachment_count=attachment_count,
        )

    @classmethod
    def _get_attachment_info(cls, message) -> tuple[list[str], bool, int]:
        """
        Extract attachment information from the message.
        
        Returns:
            tuple containing:
            - list[str]: List of attachment types
            - bool: Whether message has file attachments
            - int: Total count of attachments
        """
        attachments = message.attachments if message.attachments else []
        attachment_types = [att.odata_type for att in attachments]
        has_file_attachments = any(att_type == "#microsoft.graph.fileAttachment" for att_type in attachment_types)
        attachment_count = len(attachments)
        return attachment_types, has_file_attachments, attachment_count

    @classmethod
    def _has_inline_attachments(cls, body_content: str) -> bool:
        """
        Check for inline attachments in HTML content by looking for 'cid:' in src attributes.
        According to Microsoft Graph documentation, inline attachments are determined by
        src attributes containing 'cid:' prefix.

        SEE: the hasAttachments property in the link above.
        """
        if not body_content:
            return False
        soup = BeautifulSoup(body_content, 'html.parser')
        elements_with_src = soup.find_all(src=True)
        return any(element['src'].startswith('cid:') for element in elements_with_src)
