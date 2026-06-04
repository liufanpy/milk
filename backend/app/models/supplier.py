from sqlalchemy import Column, Integer, String
from app.database import Base


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    contact = Column(String(100), default="")
    phone = Column(String(50), default="")
