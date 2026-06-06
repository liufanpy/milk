from pydantic import BaseModel
from typing import List, Optional


class WastageItem(BaseModel):
    product_id: int
    quantity: int
    reason: str


class WastageCreate(BaseModel):
    items: List[WastageItem]
    note: str = ""
