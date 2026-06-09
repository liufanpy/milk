from datetime import date, datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


class InventoryCheck(Base):
    __tablename__ = "inventory_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(20), unique=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    check_date = Column(Date, default=date.today)
    status = Column(String(20), default="confirmed")
    note = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.now)


class InventoryCheckItem(Base):
    __tablename__ = "inventory_check_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    check_id = Column(Integer, ForeignKey("inventory_checks.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    actual_quantity = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("check_id", "product_id", name="uq_check_product"),
    )
