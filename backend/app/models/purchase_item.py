from datetime import date
from sqlalchemy import Column, Integer, Float, Date, ForeignKey
from app.database import Base


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0.0)
    production_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
