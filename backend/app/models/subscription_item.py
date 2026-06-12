from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, ForeignKey, DateTime
from app.database import Base


class SubscriptionItem(Base):
    __tablename__ = "subscription_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0.0)
    is_promo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
