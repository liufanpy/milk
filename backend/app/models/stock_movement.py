from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum
from app.database import Base
from app.enums import Direction, DocumentType


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    direction = Column(Enum(Direction), nullable=False)
    quantity = Column(Integer, nullable=False)
    source_type = Column(Enum(DocumentType), nullable=True)
    source_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
