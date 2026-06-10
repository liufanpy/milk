from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.database import Base


class WastageOrder(Base):
    __tablename__ = "wastage_orders"

    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True)
    status = Column(String(20), default="confirmed")
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
