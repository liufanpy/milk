from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    address = Column(String(200), default="")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)
