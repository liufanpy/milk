from pydantic import BaseModel, Field
from typing import Optional


class CustomerCreate(BaseModel):
    name: str = Field(..., max_length=200)
    phone: str = ""
    contact: str = ""
    address: str = ""
    price_tier: str = "retail"
    default_payment: str = "现结"


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    price_tier: Optional[str] = None
    default_payment: Optional[str] = None


class CustomerOut(BaseModel):
    id: int
    name: str
    phone: str
    contact: str
    address: str
    price_tier: str
    default_payment: str

    class Config:
        from_attributes = True
