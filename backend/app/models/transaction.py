from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Enum, Index
from app.database import Base
from app.enums import TransactionCategory, DocumentType


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(Enum(TransactionCategory, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    amount = Column(Float, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    source_type = Column(Enum(DocumentType, values_callable=lambda obj: [e.value for e in obj]), nullable=True)
    source_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index("ix_transactions_customer_time", "customer_id", "created_at"),
    )
