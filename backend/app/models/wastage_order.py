from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class WastageOrder(Base):
    __tablename__ = "wastage_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(20), nullable=True, unique=True, index=True)
    note = Column(String(500), default="")
    status = Column(String(20), default="confirmed")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
