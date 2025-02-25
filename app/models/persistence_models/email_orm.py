from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from app.persistence.base_connection import Base

class DBEmail(Base):
    __tablename__ = "tbl_email_v2"

    # Expected from front-end
    email_id = Column(Integer, primary_key=True, autoincrement=True)
    ref_id = Column(Integer, nullable=False)
    ref_type = Column(String(20), nullable=False, index=True)

    # Fields from our graph model (email)
    from_addr = Column(String(250), nullable=False)
    subject = Column(String(250))
    body = Column(Text)
    email_date = Column(DateTime, nullable=False)
    created_by = Column(Integer, nullable=False)
    created_date = Column(DateTime, nullable=False, server_default='CURRENT_TIMESTAMP')
    graph_message_id = Column(String(350), unique=True)
    graph_source_id = Column(String(350))
    graph_conversation_id = Column(String(350))
    is_read = Column(Boolean)
    has_attachments = Column(Boolean)

    # Relationship to recipients
    recipients = relationship("DBEmailRecipient", back_populates="email", cascade="all, delete-orphan")