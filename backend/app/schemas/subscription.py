from pydantic import BaseModel
from typing import List, Optional


class SubscriptionCreate(BaseModel):
    customer_id: int
    paid_amount: float
    is_paid: bool = True
    note: str = ""


class SubscriptionDeductItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: Optional[float] = None
    is_promo: bool = False


class SubscriptionDeduct(BaseModel):
    items: List[SubscriptionDeductItem]
