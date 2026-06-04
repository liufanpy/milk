from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    brand = Column(String(100), default="")
    category = Column(String(50), default="")
    unit = Column(String(20), default="箱")
    barcode = Column(String(100), default="")
    spec = Column(String(100), default="")
    default_purchase_price = Column(Float, default=0.0)
    default_retail_price = Column(Float, default=0.0)
    default_wholesale_price = Column(Float, default=0.0)
    shelf_life_days = Column(Integer, default=0)
