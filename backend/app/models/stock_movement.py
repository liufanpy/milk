from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum, Index
from app.database import Base
from app.enums import Direction, DocumentType


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    direction = Column(Enum(Direction, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    quantity = Column(Integer, nullable=False)
    source_type = Column(Enum(DocumentType, values_callable=lambda obj: [e.value for e in obj]), nullable=True)
    source_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index("ix_stock_movements_product_store", "product_id", "store_id"),
        Index("ix_stock_movements_product_time", "product_id", "created_at"),
    )
