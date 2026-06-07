from pydantic import BaseModel
from typing import List, Optional


class ReturnItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float
    is_wasted: bool = False


class ReturnCreate(BaseModel):
    customer_id: int
    source_type: Optional[str] = None   # 'delivery' | 'retail' | 'subscription'
    source_order_id: Optional[int] = None
    items: List[ReturnItem]
    note: str = ""
