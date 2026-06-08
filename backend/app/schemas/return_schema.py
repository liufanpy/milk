from pydantic import BaseModel
from typing import List, Optional


class ReturnItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class ReturnCreate(BaseModel):
    customer_id: int
    items: List[ReturnItem]
    note: str = ""
