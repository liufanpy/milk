from sqlalchemy import Column, Integer, Float, String, ForeignKey
from app.database import Base


class RetailItem(Base):
    __tablename__ = "retail_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    discount_reason = Column(String(50), default="")
