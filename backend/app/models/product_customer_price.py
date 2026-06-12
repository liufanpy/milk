from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint, Index
from app.database import Base


class ProductCustomerPrice(Base):
    __tablename__ = "product_customer_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    price = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("product_id", "customer_id", name="uq_product_customer"),
        Index("ix_pcp_customer", "customer_id"),
    )
