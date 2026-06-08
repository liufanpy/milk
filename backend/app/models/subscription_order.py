from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base


class SubscriptionOrder(Base):
    __tablename__ = "subscription_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(20), nullable=True, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    paid_amount = Column(Float, nullable=False)
    remaining_amount = Column(Float, nullable=False)
    note = Column(String(500), default="")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)
