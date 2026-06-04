from pydantic import BaseModel, Field
from typing import Optional


class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=200)
    contact: str = ""
    phone: str = ""


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None


class SupplierOut(BaseModel):
    id: int
    name: str
    contact: str
    phone: str

    class Config:
        from_attributes = True
