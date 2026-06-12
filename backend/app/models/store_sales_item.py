from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base


class StoreSalesItem(Base):
    __tablename__ = "store_sales_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    beginning = Column(Integer, nullable=False, default=0)
    received = Column(Integer, nullable=False, default=0)
    actual_quantity = Column(Integer, nullable=False)

    @property
    def sales_quantity(self) -> int:
        return self.beginning + self.received - self.actual_quantity
