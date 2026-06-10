from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base


class StoreSalesItem(Base):
    __tablename__ = "store_sales_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    beginning = Column(Integer, nullable=False, default=0)
    received = Column(Integer, nullable=False, default=0)
    actual_quantity = Column(Integer, nullable=False)
    sales_quantity = Column(Integer, nullable=False, default=0)
