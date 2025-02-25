from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.persistence.base_connection import Base

"""
Based on an outdated model, working on a decomposition currently
"""
class DBEmail(Base):
    __tablename__ = "tbl_email"

    # Expected from front-end
    id = Column(Integer, primary_key=True, autoincrement=True)
    ref_id = Column(Integer, nullable=False)
    ref_type = Column(String(20), nullable=False)

    # Fields from our graph model (email)
    from_addr = Column(String(250), nullable=False)
    to_addr = Column(String(10000))
    subject = Column(String(250))
    body = Column(Text)
    email_date = Column(DateTime, nullable=False)
    created_by = Column(Integer, nullable=False)
    created_date = Column(DateTime, nullable=False, server_default='CURRENT_TIMESTAMP')
    rmc_include = Column(Boolean, default=False, nullable=False)
    vendor_include = Column(Boolean, default=False, nullable=False)
    cc_addr = Column(String(10000))
    bcc_addr = Column(String(10000))
    graph_message_id = Column(String(350))
    graph_source_id = Column(String(350))
    graph_conversation_id = Column(String(350))
    is_read = Column(Boolean)
    has_attachments = Column(Boolean)