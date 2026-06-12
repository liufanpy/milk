from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base


class InventoryCheckItem(Base):
    __tablename__ = "inventory_check_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    theoretical_qty = Column(Integer, nullable=False, default=0)
    actual_qty = Column(Integer, nullable=True)
    difference = Column(Integer, nullable=False, default=0)
