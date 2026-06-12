from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum
from app.database import Base
from app.enums import DocumentType


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_type = Column(Enum(DocumentType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    order_number = Column(String(20), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
