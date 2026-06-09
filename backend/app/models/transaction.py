from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    category = Column(String(30), nullable=False)
    amount = Column(Float, nullable=False)
    source_type = Column(String(20), nullable=True)
    source_id = Column(Integer, nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
