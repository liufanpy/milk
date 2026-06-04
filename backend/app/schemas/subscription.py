from pydantic import BaseModel
from typing import List


class SubscriptionCreate(BaseModel):
    customer_id: int
    total_amount: float
    total_bottles: int
    paid_bottles: int = 0
    free_bottles: int = 0


class SubscriptionDeductItem(BaseModel):
    product_id: int
    quantity: int


class SubscriptionDeduct(BaseModel):
    items: List[SubscriptionDeductItem]
    shelf_id: int
