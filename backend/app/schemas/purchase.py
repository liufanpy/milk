from pydantic import BaseModel
from typing import List


class PurchaseItem(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float
    shelf_id: int


class PurchaseCreate(BaseModel):
    supplier_id: int
    items: List[PurchaseItem]
    note: str = ""
