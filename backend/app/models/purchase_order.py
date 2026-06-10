from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from app.database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_date = Column(Date, default=date.today)
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default="draft")
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
