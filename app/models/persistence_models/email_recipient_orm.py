from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.persistence.base_connection import Base
from app.models.persistence_models.email_recipient_types import RecipientType

class DBEmailRecipient(Base):
    __tablename__ = "tbl_email_recipients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey('tbl_email_v2.email_id'), nullable=False, index=True)
    email_address = Column(String(250), nullable=False, index=True)
    recipient_type = Column(Enum(RecipientType), nullable=False)

    # Relationship back to the parent email
    email = relationship("DBEmail", back_populates="recipients") 