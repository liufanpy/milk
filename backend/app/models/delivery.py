from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from app.database import Base


class Delivery(Base):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(20), nullable=True, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    delivery_date = Column(Date, default=date.today)
    status = Column(String(20), default="pending")
    subscription_order_id = Column(Integer, ForeignKey("subscription_orders.id"), nullable=True)
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
