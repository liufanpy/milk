from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from app.database import Base


class InventoryCheck(Base):
    __tablename__ = "inventory_checks"

    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True)
    check_date = Column(Date, default=date.today)
    status = Column(String(20), default="draft")
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    confirmed_at = Column(DateTime, nullable=True)
