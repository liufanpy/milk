from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from app.database import Base


class DistributionOrder(Base):
    __tablename__ = "distribution_orders"

    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    delivery_date = Column(Date, default=date.today)
    subscription_order_id = Column(Integer, ForeignKey("subscription_orders.document_id"), nullable=True)
    status = Column(String(20), default="pending")
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
