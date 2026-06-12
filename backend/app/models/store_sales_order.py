from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from app.database import Base


class StoreSalesOrder(Base):
    __tablename__ = "store_sales_orders"

    document_id = Column(Integer, ForeignKey("documents.id"), primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    check_date = Column(Date, default=date.today)
    status = Column(String(20), default="confirmed")
    last_movement_id = Column(Integer, default=0)
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)
