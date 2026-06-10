from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum
from app.database import Base
from app.enums import TransactionCategory, DocumentType


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(Enum(TransactionCategory), nullable=False)
    amount = Column(Float, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    source_type = Column(Enum(DocumentType), nullable=True)
    source_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
