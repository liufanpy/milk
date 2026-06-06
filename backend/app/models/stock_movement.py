from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.database import Base


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    direction = Column(String(10), nullable=False)
    reason = Column(String(30), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0.0)
    delivery_id = Column(Integer, ForeignKey("deliveries.id"), nullable=True)
    subscription_order_id = Column(Integer, ForeignKey("subscription_orders.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    retail_order_id = Column(Integer, ForeignKey("retail_orders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
