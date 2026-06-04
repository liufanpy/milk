from pydantic import BaseModel, Field
from typing import Optional


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    brand: str = ""
    category: str = ""
    unit: str = "箱"
    barcode: str = ""
    default_retail_price: float = 0.0
    default_wholesale_price: float = 0.0
    shelf_life_days: int = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    barcode: Optional[str] = None
    default_retail_price: Optional[float] = None
    default_wholesale_price: Optional[float] = None
    shelf_life_days: Optional[int] = None


class ProductOut(BaseModel):
    id: int
    name: str
    brand: str
    category: str
    unit: str
    barcode: str
    default_retail_price: float
    default_wholesale_price: float
    shelf_life_days: int

    class Config:
        from_attributes = True
