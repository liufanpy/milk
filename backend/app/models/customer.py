from sqlalchemy import Column, Integer, String
from app.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(50), default="")
    contact = Column(String(100), default="")
    address = Column(String(500), default="")
    price_tier = Column(String(20), default="retail")
    default_payment = Column(String(20), default="现结")
