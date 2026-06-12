from sqlalchemy import Column, Integer, Float, String, ForeignKey
from app.database import Base


class WastageItem(Base):
    __tablename__ = "wastage_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0.0)
    reason = Column(String(20), nullable=False)
    source_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
