from pydantic import BaseModel
from typing import List, Optional


class SaleItem(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class SaleCreate(BaseModel):
    customer_id: Optional[int] = None
    items: List[SaleItem]
    paid: bool = True
    note: str = ""


class SaleOrderOut(BaseModel):
    id: int
    customer_id: int | None
    customer_name: str
    item_count: int
    total_amount: float
    paid: bool
    status: str
    items_summary: str
    created_at: str

    class Config:
        from_attributes = True


class SaleOrderDetail(SaleOrderOut):
    items: list[dict]
