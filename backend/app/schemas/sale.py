from pydantic import BaseModel
from typing import List, Optional


class SaleItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    shelf_id: int


class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[SaleItem]
    paid: bool = True
    note: str = ""
