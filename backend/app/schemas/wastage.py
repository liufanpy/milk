from pydantic import BaseModel
from typing import List


class WastageItem(BaseModel):
    product_id: int
    quantity: int


class WastageCreate(BaseModel):
    items: List[WastageItem]
    note: str = ""
