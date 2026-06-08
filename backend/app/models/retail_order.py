from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from app.database import Base


class RetailOrder(Base):
    __tablename__ = "retail_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(20), nullable=True, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    status = Column(String(20), nullable=False, default="confirmed")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
