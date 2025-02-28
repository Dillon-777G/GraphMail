# Standard library imports
from typing import Literal, Optional, Union

# Third party imports
from msgraph.generated.models.attachment import Attachment
from msgraph.generated.models.attachment_collection_response import AttachmentCollectionResponse
from pydantic import BaseModel, Field

# Local imports
from app.error_handling.exceptions.email_attachment_exception import EmailAttachmentException

"""
NOTE:
This class is currently only designed for the file attachment resource. More logic will
have to be added in order to support itemAttachment and referenceAttachment.

Links:
- fileAttachment: https://learn.microsoft.com/en-us/graph/api/resources/fileattachment?view=graph-rest-1.0
- itemAttachment: https://learn.microsoft.com/en-us/graph/api/resources/itemattachment?view=graph-rest-1.0
- referenceAttachment: https://learn.microsoft.com/en-us/graph/api/resources/referenceattachment?view=graph-rest-1.0
"""

class EmailAttachment(BaseModel):
    """
    Represents an email attachment.

    Attributes:
        id (str): Unique identifier of the attachment.
        name (str): File name of the attachment.
        content_type (str): MIME type of the attachment.
        size (int): Size of the attachment in bytes.
        is_inline (bool): Whether the attachment is inline.
        odata_type (Literal): Type of attachment, currently only supporting fileAttachment.
        content_bytes (Optional[str]): Base64 encoded content of the attachment.
    """
    id: str = Field(..., description="Unique identifier of the attachment")
    name: str = Field(..., description="File name of the attachment")
    content_type: str = Field(..., description="MIME type of the attachment")
    size: int = Field(..., ge=0, description="Size of the attachment in bytes")
    is_inline: bool = Field(default=False, description="Whether the attachment is inline")
    odata_type: Literal["#microsoft.graph.fileAttachment"] = Field(
        ..., 
        description="Type of attachment, currently only supporting fileAttachment"
    )
    content_bytes: Optional[str] = Field(
        default=None, 
        description="Base64 encoded content of the attachment"
    )

    @classmethod
    def graph_email_attachment(cls, attachment: Union[Attachment, AttachmentCollectionResponse]) -> "EmailAttachment":
        """
        Create an EmailAttachment from either a Graph Attachment or AttachmentCollectionResponse.

        Args:
            attachment: Either a Graph Attachment or AttachmentCollectionResponse object.

        Returns:
            EmailAttachment: A new EmailAttachment instance.
        """
        if isinstance(attachment, AttachmentCollectionResponse):
            if not attachment.value or len(attachment.value) == 0:
                raise EmailAttachmentException(detail="No attachments found in collection", status_code=400)
            attachment = attachment.value[0]

        return cls(
            id=attachment.id,
            name=attachment.name,
            content_type=attachment.content_type,
            size=attachment.size,
            is_inline=getattr(attachment, "is_inline", False),
            odata_type=attachment.odata_type,
            content_bytes=getattr(attachment, "content_bytes", None),
        )

    def is_valid_file_attachment(self) -> None:
        """
        Validate if the attachment is a valid fileAttachment.

        Raises:
            EmailAttachmentException: If the attachment is not a valid fileAttachment.
        """
        if self.odata_type != "#microsoft.graph.fileAttachment":
            raise EmailAttachmentException(detail=f"Attachment {self.id} is not a fileAttachment.", status_code=400)
        if not self.content_bytes:
            raise EmailAttachmentException(detail=f"Attachment {self.id} has no contentBytes.", status_code=400)
